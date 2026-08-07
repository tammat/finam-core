#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import pathlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Iterable, Mapping, Sequence

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    discover_bar_contract,
)


SOURCE_VERSION = "POSTGRESQL_EDGE_FAILURE_ATTRIBUTION_V1"

DEFAULT_OUTPUT_ROOT = pathlib.Path(
    "/tmp/postgresql_edge_failure_attribution_v1"
)

DEFAULT_BAR_SCHEMA = "public"
DEFAULT_BAR_TABLE = "market_bars"

MINIMUM_GROUP_TRADES = 30


@dataclass(frozen=True, slots=True)
class Bar:
    ts: datetime
    high: Decimal
    low: Decimal


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")

    return Decimal(str(value))


def decimal_div(
    numerator: Decimal,
    denominator: Decimal | int,
) -> Decimal:
    denominator_decimal = Decimal(str(denominator))

    if denominator_decimal == 0:
        return Decimal("0")

    return numerator / denominator_decimal


def write_tsv(
    path: pathlib.Path,
    fields: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(fields),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def profit_factor(values: Sequence[Decimal]) -> Decimal:
    gains = sum(
        (value for value in values if value > 0),
        Decimal("0"),
    )
    losses = abs(
        sum(
            (value for value in values if value < 0),
            Decimal("0"),
        )
    )

    if losses > 0:
        return gains / losses

    return gains if gains > 0 else Decimal("0")


def load_trades(
    cursor: RealDictCursor,
    batch_id: str,
) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            r.run_uuid::text,
            r.research_batch_id,
            r.research_code,
            r.strategy_code,
            r.strategy_version,
            r.symbol,
            r.timeframe,
            r.parameter_hash,
            r.parameter_json,
            r.status_code,
            t.trade_no,
            t.side,
            t.entry_ts,
            t.exit_ts,
            t.entry_price,
            t.exit_price,
            t.gross_pnl,
            t.commission,
            t.slippage,
            t.net_pnl
        FROM analytics.edge_lab_run_v1 r
        JOIN analytics.research_trade_v1 t
          ON t.run_uuid = r.run_uuid
        WHERE r.research_batch_id = %s
        ORDER BY
            r.strategy_code,
            r.symbol,
            r.run_uuid,
            t.trade_no
        """,
        (batch_id,),
    )

    return [
        dict(row)
        for row in cursor.fetchall()
    ]


def load_run_count(
    cursor: RealDictCursor,
    batch_id: str,
) -> dict[str, int]:
    cursor.execute(
        """
        SELECT
            count(*)::bigint AS total_runs,
            count(*) FILTER (
                WHERE status_code = 'DONE'
            )::bigint AS done_runs,
            count(*) FILTER (
                WHERE status_code = 'QUEUED'
            )::bigint AS queued_runs,
            count(*) FILTER (
                WHERE status_code = 'FAILED'
            )::bigint AS failed_runs
        FROM analytics.edge_lab_run_v1
        WHERE research_batch_id = %s
        """,
        (batch_id,),
    )

    row = cursor.fetchone()

    return {
        key: int(row[key])
        for key in (
            "total_runs",
            "done_runs",
            "queued_runs",
            "failed_runs",
        )
    }


def load_bars(
    cursor: RealDictCursor,
    *,
    schema_name: str,
    table_name: str,
    symbol_value: str,
    timeframe_value: str,
) -> list[Bar]:
    contract = discover_bar_contract(
        cursor,
        schema_name,
        table_name,
    )

    timestamp_column = str(contract["timestamp"])
    symbol_column = str(contract["symbol"])
    timeframe_column = contract["timeframe"]

    predicates = [
        sql.SQL("{} = %s").format(
            sql.Identifier(symbol_column)
        )
    ]
    values: list[Any] = [symbol_value]

    if timeframe_column is not None:
        predicates.append(
            sql.SQL("{} = %s").format(
                sql.Identifier(str(timeframe_column))
            )
        )
        values.append(timeframe_value)

    query = sql.SQL(
        """
        SELECT
            {timestamp_column} AS ts,
            high,
            low
        FROM {schema_name}.{table_name}
        WHERE {predicates}
        ORDER BY {timestamp_column}
        """
    ).format(
        timestamp_column=sql.Identifier(timestamp_column),
        schema_name=sql.Identifier(schema_name),
        table_name=sql.Identifier(table_name),
        predicates=sql.SQL(" AND ").join(predicates),
    )

    cursor.execute(query, values)

    return [
        Bar(
            ts=row["ts"],
            high=to_decimal(row["high"]),
            low=to_decimal(row["low"]),
        )
        for row in cursor.fetchall()
    ]


def parameter_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if isinstance(value, str):
        return dict(json.loads(value))

    return {}


def enrich_with_excursions(
    trades: list[dict[str, Any]],
    bars_by_market: Mapping[tuple[str, str], Sequence[Bar]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    enriched: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    timestamp_cache = {
        key: [bar.ts for bar in bars]
        for key, bars in bars_by_market.items()
    }

    for trade in trades:
        key = (
            str(trade["symbol"]),
            str(trade["timeframe"]),
        )
        bars = bars_by_market.get(key)
        timestamps = timestamp_cache.get(key)

        if not bars or not timestamps:
            unresolved.append(
                {
                    "scope": "MARKET_BARS",
                    "identity": f"{key[0]}:{key[1]}",
                    "reason": "BAR_SERIES_MISSING",
                }
            )
            continue

        entry_ts = trade["entry_ts"]
        exit_ts = trade["exit_ts"]

        entry_index = bisect.bisect_left(
            timestamps,
            entry_ts,
        )
        exit_index = bisect.bisect_right(
            timestamps,
            exit_ts,
        ) - 1

        if (
            entry_index >= len(bars)
            or exit_index < entry_index
        ):
            unresolved.append(
                {
                    "scope": "TRADE_BAR_WINDOW",
                    "identity": (
                        f"{trade['run_uuid']}:"
                        f"{trade['trade_no']}"
                    ),
                    "reason": "TRADE_BAR_WINDOW_NOT_FOUND",
                }
            )
            continue

        interval = bars[entry_index:exit_index + 1]

        if not interval:
            unresolved.append(
                {
                    "scope": "TRADE_BAR_WINDOW",
                    "identity": (
                        f"{trade['run_uuid']}:"
                        f"{trade['trade_no']}"
                    ),
                    "reason": "TRADE_BAR_WINDOW_EMPTY",
                }
            )
            continue

        parameters = parameter_dict(
            trade["parameter_json"]
        )
        quantity = to_decimal(
            parameters.get("quantity", 1)
        )

        entry_price = to_decimal(trade["entry_price"])
        max_high = max(bar.high for bar in interval)
        min_low = min(bar.low for bar in interval)

        side = str(trade["side"]).upper()

        if side == "LONG":
            mfe = max(
                Decimal("0"),
                (max_high - entry_price) * quantity,
            )
            mae = max(
                Decimal("0"),
                (entry_price - min_low) * quantity,
            )
        elif side == "SHORT":
            mfe = max(
                Decimal("0"),
                (entry_price - min_low) * quantity,
            )
            mae = max(
                Decimal("0"),
                (max_high - entry_price) * quantity,
            )
        else:
            unresolved.append(
                {
                    "scope": "TRADE_SIDE",
                    "identity": (
                        f"{trade['run_uuid']}:"
                        f"{trade['trade_no']}"
                    ),
                    "reason": f"UNSUPPORTED_SIDE:{side}",
                }
            )
            continue

        net_pnl = to_decimal(trade["net_pnl"])
        commission = to_decimal(trade["commission"])
        slippage = to_decimal(trade["slippage"])

        execution_pnl = net_pnl + commission
        market_pnl = execution_pnl + slippage

        capture_ratio = (
            market_pnl / mfe
            if mfe > 0
            else Decimal("0")
        )

        holding_seconds = Decimal(
            str((exit_ts - entry_ts).total_seconds())
        )

        enriched.append(
            {
                **trade,
                "entry_hour_utc": entry_ts.hour,
                "holding_seconds": holding_seconds,
                "holding_minutes": (
                    holding_seconds / Decimal("60")
                ),
                "holding_bar_count": len(interval),
                "market_pnl_before_costs": market_pnl,
                "execution_pnl_after_slippage": (
                    execution_pnl
                ),
                "net_pnl_after_costs": net_pnl,
                "mfe": mfe,
                "mae": mae,
                "capture_ratio": capture_ratio,
            }
        )

    return enriched, unresolved


def classify_attribution(
    *,
    market_expectancy: Decimal,
    execution_expectancy: Decimal,
    net_expectancy: Decimal,
) -> str:
    if market_expectancy <= 0:
        return "NEGATIVE_BEFORE_COSTS"

    if execution_expectancy <= 0:
        return "SLIPPAGE_DESTROYS_GROSS_EDGE"

    if net_expectancy <= 0:
        return "COMMISSION_DESTROYS_EXECUTION_EDGE"

    return "POSITIVE_AFTER_COSTS"


def aggregate_rows(
    rows: Sequence[dict[str, Any]],
    key_fields: Sequence[str],
) -> list[dict[str, Any]]:
    groups: dict[
        tuple[Any, ...],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in rows:
        key = tuple(row[field] for field in key_fields)
        groups[key].append(row)

    output: list[dict[str, Any]] = []

    for key, group_rows in groups.items():
        trade_count = len(group_rows)

        market_values = [
            to_decimal(row["market_pnl_before_costs"])
            for row in group_rows
        ]
        execution_values = [
            to_decimal(
                row["execution_pnl_after_slippage"]
            )
            for row in group_rows
        ]
        net_values = [
            to_decimal(row["net_pnl_after_costs"])
            for row in group_rows
        ]

        market_sum = sum(market_values, Decimal("0"))
        execution_sum = sum(
            execution_values,
            Decimal("0"),
        )
        net_sum = sum(net_values, Decimal("0"))
        commission_sum = sum(
            (
                to_decimal(row["commission"])
                for row in group_rows
            ),
            Decimal("0"),
        )
        slippage_sum = sum(
            (
                to_decimal(row["slippage"])
                for row in group_rows
            ),
            Decimal("0"),
        )
        mfe_sum = sum(
            (
                to_decimal(row["mfe"])
                for row in group_rows
            ),
            Decimal("0"),
        )
        mae_sum = sum(
            (
                to_decimal(row["mae"])
                for row in group_rows
            ),
            Decimal("0"),
        )

        market_expectancy = decimal_div(
            market_sum,
            trade_count,
        )
        execution_expectancy = decimal_div(
            execution_sum,
            trade_count,
        )
        net_expectancy = decimal_div(
            net_sum,
            trade_count,
        )

        positive_market = sum(
            value > 0
            for value in market_values
        )
        positive_net = sum(
            value > 0
            for value in net_values
        )

        capture_ratios = [
            to_decimal(row["capture_ratio"])
            for row in group_rows
            if to_decimal(row["mfe"]) > 0
        ]

        base = {
            field: value
            for field, value in zip(key_fields, key)
        }

        output.append(
            {
                **base,
                "trades": trade_count,
                "market_pnl_sum": market_sum,
                "execution_pnl_sum": execution_sum,
                "net_pnl_sum": net_sum,
                "commission_sum": commission_sum,
                "slippage_sum": slippage_sum,
                "total_cost_sum": (
                    commission_sum + slippage_sum
                ),
                "market_expectancy": market_expectancy,
                "execution_expectancy": (
                    execution_expectancy
                ),
                "net_expectancy": net_expectancy,
                "slippage_impact_per_trade": decimal_div(
                    slippage_sum,
                    trade_count,
                ),
                "commission_impact_per_trade": decimal_div(
                    commission_sum,
                    trade_count,
                ),
                "market_profit_factor": profit_factor(
                    market_values
                ),
                "net_profit_factor": profit_factor(
                    net_values
                ),
                "market_win_rate": (
                    Decimal(positive_market)
                    / Decimal(trade_count)
                    * Decimal("100")
                ),
                "net_win_rate": (
                    Decimal(positive_net)
                    / Decimal(trade_count)
                    * Decimal("100")
                ),
                "avg_mfe": decimal_div(
                    mfe_sum,
                    trade_count,
                ),
                "avg_mae": decimal_div(
                    mae_sum,
                    trade_count,
                ),
                "avg_capture_ratio": (
                    decimal_div(
                        sum(
                            capture_ratios,
                            Decimal("0"),
                        ),
                        len(capture_ratios),
                    )
                    if capture_ratios
                    else Decimal("0")
                ),
                "attribution_classification": (
                    classify_attribution(
                        market_expectancy=market_expectancy,
                        execution_expectancy=(
                            execution_expectancy
                        ),
                        net_expectancy=net_expectancy,
                    )
                ),
                "sample_status": (
                    "SUFFICIENT"
                    if trade_count >= MINIMUM_GROUP_TRADES
                    else "INSUFFICIENT"
                ),
            }
        )

    output.sort(
        key=lambda row: (
            *(
                str(row[field])
                for field in key_fields
            ),
        )
    )

    return output


AGGREGATE_FIELDS = (
    "trades",
    "market_pnl_sum",
    "execution_pnl_sum",
    "net_pnl_sum",
    "commission_sum",
    "slippage_sum",
    "total_cost_sum",
    "market_expectancy",
    "execution_expectancy",
    "net_expectancy",
    "slippage_impact_per_trade",
    "commission_impact_per_trade",
    "market_profit_factor",
    "net_profit_factor",
    "market_win_rate",
    "net_win_rate",
    "avg_mfe",
    "avg_mae",
    "avg_capture_ratio",
    "attribution_classification",
    "sample_status",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Edge Failure Attribution V1"
        )
    )
    parser.add_argument(
        "--batch-id",
        required=True,
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = (
        pathlib.Path(args.output_root)
        / args.batch_id
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            run_counts = load_run_count(
                cursor,
                args.batch_id,
            )
            trades = load_trades(
                cursor,
                args.batch_id,
            )

            markets = sorted(
                {
                    (
                        str(row["symbol"]),
                        str(row["timeframe"]),
                    )
                    for row in trades
                }
            )

            bars_by_market: dict[
                tuple[str, str],
                list[Bar],
            ] = {}

            for symbol_value, timeframe_value in markets:
                sample_trade = next(
                    row
                    for row in trades
                    if row["symbol"] == symbol_value
                    and row["timeframe"] == timeframe_value
                )
                parameters = parameter_dict(
                    sample_trade["parameter_json"]
                )

                schema_name = str(
                    parameters.get(
                        "bar_schema",
                        DEFAULT_BAR_SCHEMA,
                    )
                )
                table_name = str(
                    parameters.get(
                        "bar_table",
                        DEFAULT_BAR_TABLE,
                    )
                )

                bars = load_bars(
                    cursor,
                    schema_name=schema_name,
                    table_name=table_name,
                    symbol_value=symbol_value,
                    timeframe_value=timeframe_value,
                )

                if not bars:
                    unresolved.append(
                        {
                            "scope": "MARKET_BARS",
                            "identity": (
                                f"{symbol_value}:"
                                f"{timeframe_value}"
                            ),
                            "reason": "NO_BARS",
                        }
                    )
                else:
                    bars_by_market[
                        (
                            symbol_value,
                            timeframe_value,
                        )
                    ] = bars

    enriched, excursion_unresolved = (
        enrich_with_excursions(
            trades,
            bars_by_market,
        )
    )
    unresolved.extend(excursion_unresolved)

    run_rows = aggregate_rows(
        enriched,
        ("run_uuid",),
    )
    family_symbol_rows = aggregate_rows(
        enriched,
        (
            "strategy_code",
            "symbol",
            "timeframe",
        ),
    )
    side_rows = aggregate_rows(
        enriched,
        (
            "strategy_code",
            "symbol",
            "side",
        ),
    )
    entry_hour_rows = aggregate_rows(
        enriched,
        (
            "strategy_code",
            "symbol",
            "entry_hour_utc",
        ),
    )
    hold_rows = aggregate_rows(
        enriched,
        (
            "strategy_code",
            "symbol",
            "holding_bar_count",
        ),
    )
    excursion_rows = aggregate_rows(
        enriched,
        (
            "strategy_code",
            "symbol",
            "side",
            "holding_bar_count",
        ),
    )

    batch_rows = aggregate_rows(
        enriched,
        ("research_batch_id",),
    )

    write_tsv(
        output_dir / "batch_summary.tsv",
        (
            "research_batch_id",
            *AGGREGATE_FIELDS,
        ),
        batch_rows,
    )
    write_tsv(
        output_dir / "run_attribution.tsv",
        (
            "run_uuid",
            *AGGREGATE_FIELDS,
        ),
        run_rows,
    )
    write_tsv(
        output_dir / "family_symbol_attribution.tsv",
        (
            "strategy_code",
            "symbol",
            "timeframe",
            *AGGREGATE_FIELDS,
        ),
        family_symbol_rows,
    )
    write_tsv(
        output_dir / "side_attribution.tsv",
        (
            "strategy_code",
            "symbol",
            "side",
            *AGGREGATE_FIELDS,
        ),
        side_rows,
    )
    write_tsv(
        output_dir / "entry_hour_attribution.tsv",
        (
            "strategy_code",
            "symbol",
            "entry_hour_utc",
            *AGGREGATE_FIELDS,
        ),
        entry_hour_rows,
    )
    write_tsv(
        output_dir / "hold_duration_attribution.tsv",
        (
            "strategy_code",
            "symbol",
            "holding_bar_count",
            *AGGREGATE_FIELDS,
        ),
        hold_rows,
    )
    write_tsv(
        output_dir / "excursion_attribution.tsv",
        (
            "strategy_code",
            "symbol",
            "side",
            "holding_bar_count",
            *AGGREGATE_FIELDS,
        ),
        excursion_rows,
    )
    write_tsv(
        output_dir / "unresolved.tsv",
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    classification_counts: dict[str, int] = defaultdict(int)

    for row in family_symbol_rows:
        classification_counts[
            str(row["attribution_classification"])
        ] += 1

    positive_before_cost_groups = sum(
        to_decimal(row["market_expectancy"]) > 0
        for row in family_symbol_rows
    )
    positive_after_slippage_groups = sum(
        to_decimal(row["execution_expectancy"]) > 0
        for row in family_symbol_rows
    )
    positive_after_cost_groups = sum(
        to_decimal(row["net_expectancy"]) > 0
        for row in family_symbol_rows
    )

    contract_lines = [
        "POSTGRESQL EDGE FAILURE ATTRIBUTION V1",
        "======================================",
        "",
        f"BATCH_ID={args.batch_id}",
        f"TOTAL_RUN_COUNT={run_counts['total_runs']}",
        f"DONE_RUN_COUNT={run_counts['done_runs']}",
        f"QUEUED_RUN_COUNT={run_counts['queued_runs']}",
        f"FAILED_RUN_COUNT={run_counts['failed_runs']}",
        f"TRADE_ROW_COUNT={len(trades)}",
        f"ATTRIBUTED_TRADE_COUNT={len(enriched)}",
        (
            "FAMILY_SYMBOL_GROUP_COUNT="
            f"{len(family_symbol_rows)}"
        ),
        (
            "POSITIVE_BEFORE_COST_GROUP_COUNT="
            f"{positive_before_cost_groups}"
        ),
        (
            "POSITIVE_AFTER_SLIPPAGE_GROUP_COUNT="
            f"{positive_after_slippage_groups}"
        ),
        (
            "POSITIVE_AFTER_ALL_COST_GROUP_COUNT="
            f"{positive_after_cost_groups}"
        ),
        f"UNRESOLVED_COUNT={len(unresolved)}",
        "MFE_MAE_BASIS=EXECUTION_ENTRY_PRICE",
        (
            "MARKET_PNL_FORMULA="
            "NET_PNL_PLUS_COMMISSION_PLUS_SLIPPAGE"
        ),
        "DATABASE=POSTGRESQL_ONLY",
        "DB_WRITES_PERFORMED=0",
        "STRATEGY_CHANGED=0",
        "RISK_ENGINE_CHANGED=0",
        "RUNTIME_CHANGED=0",
        "EXECUTION_CHANGED=0",
        "ORDERS_CHANGED=0",
        "FILLS_CHANGED=0",
        "OOS_ALLOWED=0",
        "SHADOW_ALLOWED=0",
        "PAPER_ALLOWED=0",
        "MICRO_LIVE_ALLOWED=0",
    ]

    for classification in sorted(classification_counts):
        contract_lines.append(
            "CLASSIFICATION_COUNT_"
            f"{classification}="
            f"{classification_counts[classification]}"
        )

    (output_dir / "contract.txt").write_text(
        "\n".join(contract_lines) + "\n",
        encoding="utf-8",
    )

    print("=== POSTGRESQL EDGE FAILURE ATTRIBUTION V1 ===")
    print(f"batch_id={args.batch_id}")
    print(f"total_run_count={run_counts['total_runs']}")
    print(f"done_run_count={run_counts['done_runs']}")
    print(f"trade_row_count={len(trades)}")
    print(f"attributed_trade_count={len(enriched)}")
    print(
        "family_symbol_group_count="
        f"{len(family_symbol_rows)}"
    )
    print(
        "positive_before_cost_group_count="
        f"{positive_before_cost_groups}"
    )
    print(
        "positive_after_slippage_group_count="
        f"{positive_after_slippage_groups}"
    )
    print(
        "positive_after_all_cost_group_count="
        f"{positive_after_cost_groups}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in family_symbol_rows:
        print(
            "ATTRIBUTION_GROUP "
            f"strategy={row['strategy_code']} "
            f"symbol={row['symbol']} "
            f"trades={row['trades']} "
            f"market_expectancy={row['market_expectancy']} "
            f"execution_expectancy="
            f"{row['execution_expectancy']} "
            f"net_expectancy={row['net_expectancy']} "
            f"market_pf={row['market_profit_factor']} "
            f"net_pf={row['net_profit_factor']} "
            f"avg_mfe={row['avg_mfe']} "
            f"avg_mae={row['avg_mae']} "
            f"capture={row['avg_capture_ratio']} "
            f"classification="
            f"{row['attribution_classification']}"
        )

    print("db_writes_performed=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_FAILURE_ATTRIBUTION_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
