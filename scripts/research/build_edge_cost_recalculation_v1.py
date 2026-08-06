#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import Counter
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUT = pathlib.Path("/tmp/edge_cost_recalculation_v1")

RECALCULATED_FILE = OUT / "recalculated_edges.tsv"
SUMMARY_FILE = OUT / "reconciliation_summary.tsv"
VALIDATED_FILE = OUT / "validated_candidates.tsv"
REJECTED_FILE = OUT / "rejected_candidates.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

ABSOLUTE_TOLERANCE = Decimal("0.000001")
RELATIVE_TOLERANCE = Decimal("0.0001")
MINIMUM_TRADES = 30


def decimal_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")

    return Decimal(str(value))


def approximately_equal(
    actual: Decimal,
    expected: Decimal,
) -> bool:
    difference = abs(actual - expected)

    if difference <= ABSOLUTE_TOLERANCE:
        return True

    scale = max(
        abs(actual),
        abs(expected),
        Decimal("1"),
    )

    return difference / scale <= RELATIVE_TOLERANCE


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def calculate_max_drawdown(net_values: list[Decimal]) -> Decimal:
    equity = Decimal("0")
    peak = Decimal("0")
    maximum_drawdown = Decimal("0")

    for net_value in net_values:
        equity += net_value
        peak = max(peak, equity)
        drawdown = peak - equity
        maximum_drawdown = max(maximum_drawdown, drawdown)

    return maximum_drawdown


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []

    with psycopg2.connect(build_psycopg_url()) as connection:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                WITH trade_groups AS (
                    SELECT
                        run_uuid,
                        research_code,
                        strategy_code,
                        symbol,
                        timeframe,
                        count(*)::bigint AS trade_count,
                        count(DISTINCT trade_no)::bigint
                            AS distinct_trade_count
                    FROM analytics.research_trade_v1
                    GROUP BY
                        run_uuid,
                        research_code,
                        strategy_code,
                        symbol,
                        timeframe
                )
                SELECT
                    o.observation_uuid::text,
                    o.run_uuid::text,
                    o.research_batch_id,
                    o.research_code,
                    o.strategy_code,
                    o.strategy_version,
                    o.symbol,
                    o.timeframe,
                    o.parameter_hash,
                    o.market_regime,
                    o.trades AS declared_trades,
                    o.expectancy AS stored_expectancy,
                    o.profit_factor AS stored_profit_factor,
                    o.max_drawdown AS stored_max_drawdown,
                    o.commission AS stored_commission,
                    o.slippage AS stored_slippage,
                    o.confidence_score,
                    o.stability_score,
                    o.verdict_code,
                    o.source_version,
                    t.trade_count,
                    t.distinct_trade_count
                FROM analytics.edge_observation_v1 o
                JOIN trade_groups t
                  ON t.run_uuid = o.run_uuid
                 AND t.research_code = o.research_code
                 AND t.strategy_code = o.strategy_code
                 AND t.symbol = o.symbol
                 AND t.timeframe = o.timeframe
                WHERE t.trade_count = t.distinct_trade_count
                  AND o.trades = t.trade_count
                ORDER BY
                    o.symbol,
                    o.strategy_code,
                    o.timeframe,
                    o.run_uuid
                """
            )
            observations = [
                dict(row)
                for row in cursor.fetchall()
            ]

            recalculated_rows: list[dict[str, Any]] = []

            for observation in observations:
                cursor.execute(
                    """
                    SELECT
                        trade_no,
                        gross_pnl,
                        commission,
                        slippage,
                        net_pnl
                    FROM analytics.research_trade_v1
                    WHERE run_uuid = %s
                      AND research_code = %s
                      AND strategy_code = %s
                      AND symbol = %s
                      AND timeframe = %s
                    ORDER BY trade_no
                    """,
                    (
                        observation["run_uuid"],
                        observation["research_code"],
                        observation["strategy_code"],
                        observation["symbol"],
                        observation["timeframe"],
                    ),
                )

                trades = list(cursor.fetchall())

                gross_values = [
                    decimal_value(row["gross_pnl"])
                    for row in trades
                ]
                commission_values = [
                    decimal_value(row["commission"])
                    for row in trades
                ]
                slippage_values = [
                    decimal_value(row["slippage"])
                    for row in trades
                ]
                net_values = [
                    decimal_value(row["net_pnl"])
                    for row in trades
                ]

                trade_count = len(trades)
                gross_pnl = sum(gross_values, Decimal("0"))
                commission = sum(
                    commission_values,
                    Decimal("0"),
                )
                slippage = sum(
                    slippage_values,
                    Decimal("0"),
                )
                net_pnl = sum(net_values, Decimal("0"))

                net_identity_expected = (
                    gross_pnl - commission - slippage
                )
                net_identity_ok = approximately_equal(
                    net_pnl,
                    net_identity_expected,
                )

                expectancy = (
                    net_pnl / Decimal(trade_count)
                    if trade_count
                    else Decimal("0")
                )

                gross_profit = sum(
                    (
                        value
                        for value in net_values
                        if value > 0
                    ),
                    Decimal("0"),
                )
                gross_loss = abs(
                    sum(
                        (
                            value
                            for value in net_values
                            if value < 0
                        ),
                        Decimal("0"),
                    )
                )

                profit_factor = (
                    gross_profit / gross_loss
                    if gross_loss > 0
                    else None
                )

                max_drawdown = calculate_max_drawdown(net_values)

                stored_expectancy = decimal_value(
                    observation["stored_expectancy"]
                )
                stored_profit_factor = decimal_value(
                    observation["stored_profit_factor"]
                )
                stored_max_drawdown = decimal_value(
                    observation["stored_max_drawdown"]
                )
                stored_commission = decimal_value(
                    observation["stored_commission"]
                )
                stored_slippage = decimal_value(
                    observation["stored_slippage"]
                )

                expectancy_match = approximately_equal(
                    expectancy,
                    stored_expectancy,
                )
                commission_match = approximately_equal(
                    commission,
                    stored_commission,
                )
                slippage_match = approximately_equal(
                    slippage,
                    stored_slippage,
                )
                drawdown_match = approximately_equal(
                    max_drawdown,
                    abs(stored_max_drawdown),
                )

                profit_factor_match = (
                    profit_factor is not None
                    and approximately_equal(
                        profit_factor,
                        stored_profit_factor,
                    )
                )

                reconciliation_ok = all(
                    (
                        net_identity_ok,
                        expectancy_match,
                        profit_factor_match,
                        commission_match,
                        slippage_match,
                    )
                )

                if not net_identity_ok:
                    classification = "INVALID_TRADE_SEQUENCE"
                    reason = "NET_PNL_IDENTITY_MISMATCH"
                elif not reconciliation_ok:
                    classification = "COST_RECALCULATION_MISMATCH"
                    reason = "STORED_AND_RECALCULATED_VALUES_DIFFER"
                elif trade_count < MINIMUM_TRADES:
                    classification = "INSUFFICIENT_SAMPLE"
                    reason = (
                        f"TRADE_COUNT_BELOW_{MINIMUM_TRADES}"
                    )
                elif expectancy <= 0:
                    classification = "NEGATIVE_AFTER_COSTS"
                    reason = "NET_EXPECTANCY_NOT_POSITIVE"
                elif profit_factor is None:
                    classification = "COST_RECALCULATION_MISMATCH"
                    reason = "PROFIT_FACTOR_UNDEFINED"
                elif profit_factor <= 1:
                    classification = "NEGATIVE_AFTER_COSTS"
                    reason = "PROFIT_FACTOR_NOT_ABOVE_ONE"
                else:
                    classification = "COST_VALIDATED"
                    reason = "RECALCULATION_AND_STORED_VALUES_MATCH"

                row = {
                    **observation,
                    "recalculated_trade_count": trade_count,
                    "recalculated_gross_pnl": gross_pnl,
                    "recalculated_commission": commission,
                    "recalculated_slippage": slippage,
                    "recalculated_net_pnl": net_pnl,
                    "recalculated_expectancy": expectancy,
                    "recalculated_profit_factor": (
                        profit_factor
                        if profit_factor is not None
                        else ""
                    ),
                    "recalculated_max_drawdown": max_drawdown,
                    "net_identity_ok": int(net_identity_ok),
                    "expectancy_match": int(expectancy_match),
                    "profit_factor_match": int(
                        profit_factor_match
                    ),
                    "commission_match": int(commission_match),
                    "slippage_match": int(slippage_match),
                    "drawdown_match": int(drawdown_match),
                    "reconciliation_ok": int(reconciliation_ok),
                    "classification": classification,
                    "reason": reason,
                }

                recalculated_rows.append(row)

                if classification in {
                    "INVALID_TRADE_SEQUENCE",
                    "COST_RECALCULATION_MISMATCH",
                }:
                    unresolved.append(
                        {
                            "scope": "EDGE_COST_RECONCILIATION",
                            "identity": (
                                f"{observation['run_uuid']}:"
                                f"{observation['strategy_code']}:"
                                f"{observation['symbol']}:"
                                f"{observation['timeframe']}"
                            ),
                            "reason": reason,
                        }
                    )

    classification_counts = Counter(
        row["classification"]
        for row in recalculated_rows
    )

    validated_rows = [
        row
        for row in recalculated_rows
        if row["classification"] == "COST_VALIDATED"
    ]

    validated_rows.sort(
        key=lambda row: (
            -decimal_value(row["recalculated_expectancy"]),
            -decimal_value(
                row["recalculated_profit_factor"]
            ),
            decimal_value(row["recalculated_max_drawdown"]),
        )
    )

    rejected_rows = [
        row
        for row in recalculated_rows
        if row["classification"] != "COST_VALIDATED"
    ]

    fields = (
        "observation_uuid",
        "run_uuid",
        "research_batch_id",
        "research_code",
        "strategy_code",
        "strategy_version",
        "symbol",
        "timeframe",
        "parameter_hash",
        "market_regime",
        "declared_trades",
        "stored_expectancy",
        "stored_profit_factor",
        "stored_max_drawdown",
        "stored_commission",
        "stored_slippage",
        "confidence_score",
        "stability_score",
        "verdict_code",
        "recalculated_trade_count",
        "recalculated_gross_pnl",
        "recalculated_commission",
        "recalculated_slippage",
        "recalculated_net_pnl",
        "recalculated_expectancy",
        "recalculated_profit_factor",
        "recalculated_max_drawdown",
        "net_identity_ok",
        "expectancy_match",
        "profit_factor_match",
        "commission_match",
        "slippage_match",
        "drawdown_match",
        "reconciliation_ok",
        "classification",
        "reason",
    )

    write_tsv(
        RECALCULATED_FILE,
        fields,
        recalculated_rows,
    )

    write_tsv(
        VALIDATED_FILE,
        fields,
        validated_rows,
    )

    write_tsv(
        REJECTED_FILE,
        fields,
        rejected_rows,
    )

    summary_rows = [
        {
            "classification": classification,
            "row_count": count,
        }
        for classification, count in sorted(
            classification_counts.items()
        )
    ]

    write_tsv(
        SUMMARY_FILE,
        (
            "classification",
            "row_count",
        ),
        summary_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("EDGE COST RECALCULATION V1\n")
        stream.write("==========================\n\n")
        stream.write("MODE=READ_ONLY\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write(
            f"SAFE_SOURCE_COUNT={len(recalculated_rows)}\n"
        )
        stream.write(
            f"COST_VALIDATED_COUNT={len(validated_rows)}\n"
        )
        stream.write(
            f"REJECTED_COUNT={len(rejected_rows)}\n"
        )
        stream.write(
            f"MINIMUM_TRADES={MINIMUM_TRADES}\n"
        )
        stream.write(
            f"ABSOLUTE_TOLERANCE={ABSOLUTE_TOLERANCE}\n"
        )
        stream.write(
            f"RELATIVE_TOLERANCE={RELATIVE_TOLERANCE}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== EDGE COST RECALCULATION V1 ===")
    print(f"safe_source_count={len(recalculated_rows)}")
    print(f"cost_validated_count={len(validated_rows)}")
    print(f"rejected_count={len(rejected_rows)}")
    print(f"unresolved_count={len(unresolved)}")

    for classification, count in sorted(
        classification_counts.items()
    ):
        print(
            "COST_CLASSIFICATION "
            f"classification={classification} "
            f"count={count}"
        )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_COST_RECALCULATION_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
