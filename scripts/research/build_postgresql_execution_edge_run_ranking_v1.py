#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import pathlib
from decimal import Decimal
from typing import Any, Iterable, Sequence

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUTPUT_ROOT = pathlib.Path(
    "/tmp/postgresql_execution_edge_run_ranking_v1"
)

TARGET_STRATEGY = "MEAN_REVERSION_ZSCORE_V1"
TARGET_SYMBOL = "SBER@MISX"
TARGET_TIMEFRAME = "M5"

MINIMUM_TRADES = 30


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def write_tsv(
    path: pathlib.Path,
    fields: Sequence[str],
    rows: Iterable[dict[str, Any]],
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


def classify(
    *,
    trades: int,
    market_expectancy: Decimal,
    execution_expectancy: Decimal,
    net_expectancy: Decimal,
) -> tuple[str, str]:
    if trades < MINIMUM_TRADES:
        return "INSUFFICIENT_SAMPLE", "TRADES_BELOW_MINIMUM"

    if market_expectancy <= 0:
        return "NO_GROSS_EDGE", "MARKET_EXPECTANCY_NOT_POSITIVE"

    if execution_expectancy <= 0:
        return (
            "SLIPPAGE_REJECTED",
            "EXECUTION_EXPECTANCY_NOT_POSITIVE",
        )

    if net_expectancy <= 0:
        return (
            "EXECUTION_EDGE_SURVIVOR",
            "COMMISSION_EXCEEDS_EXECUTION_EDGE",
        )

    return "NET_EDGE_CANDIDATE", "POSITIVE_AFTER_ALL_COSTS"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Execution Edge Run Ranking V1"
        )
    )
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    output_dir = OUTPUT_ROOT / args.batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    r.run_uuid::text,
                    r.research_code,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    r.parameter_hash,
                    r.parameter_json,
                    count(*)::bigint AS trades,
                    sum(
                        t.net_pnl
                        + t.commission
                        + t.slippage
                    )::numeric AS market_pnl_sum,
                    sum(
                        t.net_pnl
                        + t.commission
                    )::numeric AS execution_pnl_sum,
                    sum(t.net_pnl)::numeric AS net_pnl_sum,
                    avg(
                        t.net_pnl
                        + t.commission
                        + t.slippage
                    )::numeric AS market_expectancy,
                    avg(
                        t.net_pnl
                        + t.commission
                    )::numeric AS execution_expectancy,
                    avg(t.net_pnl)::numeric
                        AS net_expectancy,
                    avg(t.slippage)::numeric
                        AS slippage_per_trade,
                    avg(t.commission)::numeric
                        AS commission_per_trade,
                    count(*) FILTER (
                        WHERE t.net_pnl + t.commission > 0
                    )::bigint AS execution_wins
                FROM analytics.edge_lab_run_v1 r
                JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                WHERE r.research_batch_id = %s
                  AND r.strategy_code = %s
                  AND r.symbol = %s
                  AND r.timeframe = %s
                GROUP BY
                    r.run_uuid,
                    r.research_code,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    r.parameter_hash,
                    r.parameter_json
                ORDER BY
                    execution_expectancy DESC,
                    market_expectancy DESC,
                    trades DESC
                """,
                (
                    args.batch_id,
                    TARGET_STRATEGY,
                    TARGET_SYMBOL,
                    TARGET_TIMEFRAME,
                ),
            )

            source_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

    ranking: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    for rank, row in enumerate(source_rows, start=1):
        trades = int(row["trades"])
        market_expectancy = to_decimal(
            row["market_expectancy"]
        )
        execution_expectancy = to_decimal(
            row["execution_expectancy"]
        )
        net_expectancy = to_decimal(
            row["net_expectancy"]
        )
        commission_per_trade = to_decimal(
            row["commission_per_trade"]
        )

        classification, reason = classify(
            trades=trades,
            market_expectancy=market_expectancy,
            execution_expectancy=execution_expectancy,
            net_expectancy=net_expectancy,
        )

        # Максимальная допустимая round-trip комиссия,
        # при которой expectancy после всех затрат равна нулю.
        break_even_round_trip_commission = max(
            Decimal("0"),
            execution_expectancy,
        )

        break_even_per_side_commission = (
            break_even_round_trip_commission
            / Decimal("2")
        )

        required_payoff_multiplier = (
            commission_per_trade / execution_expectancy
            if execution_expectancy > 0
            else Decimal("0")
        )

        ranking.append(
            {
                "rank": rank,
                **row,
                "execution_win_rate": (
                    Decimal(row["execution_wins"])
                    / Decimal(trades)
                    * Decimal("100")
                ),
                "break_even_round_trip_commission": (
                    break_even_round_trip_commission
                ),
                "break_even_per_side_commission": (
                    break_even_per_side_commission
                ),
                "required_execution_payoff_multiplier": (
                    required_payoff_multiplier
                ),
                "classification": classification,
                "classification_reason": reason,
            }
        )

    if not ranking:
        unresolved.append(
            {
                "scope": "RUN_RANKING",
                "identity": (
                    f"{TARGET_STRATEGY}:"
                    f"{TARGET_SYMBOL}:"
                    f"{TARGET_TIMEFRAME}"
                ),
                "reason": "NO_RUNS_FOUND",
            }
        )

    fields = (
        "rank",
        "run_uuid",
        "research_code",
        "strategy_code",
        "symbol",
        "timeframe",
        "parameter_hash",
        "parameter_json",
        "trades",
        "market_pnl_sum",
        "execution_pnl_sum",
        "net_pnl_sum",
        "market_expectancy",
        "execution_expectancy",
        "net_expectancy",
        "slippage_per_trade",
        "commission_per_trade",
        "execution_wins",
        "execution_win_rate",
        "break_even_round_trip_commission",
        "break_even_per_side_commission",
        "required_execution_payoff_multiplier",
        "classification",
        "classification_reason",
    )

    write_tsv(
        output_dir / "run_ranking.tsv",
        fields,
        ranking,
    )

    execution_survivors = [
        row
        for row in ranking
        if row["classification"] in {
            "EXECUTION_EDGE_SURVIVOR",
            "NET_EDGE_CANDIDATE",
        }
    ]

    write_tsv(
        output_dir / "execution_survivors.tsv",
        fields,
        execution_survivors,
    )

    break_even_fields = (
        "rank",
        "run_uuid",
        "parameter_hash",
        "trades",
        "execution_expectancy",
        "commission_per_trade",
        "break_even_round_trip_commission",
        "break_even_per_side_commission",
        "required_execution_payoff_multiplier",
        "classification",
    )

    write_tsv(
        output_dir / "commission_break_even.tsv",
        break_even_fields,
        execution_survivors,
    )

    write_tsv(
        output_dir / "unresolved.tsv",
        ("scope", "identity", "reason"),
        unresolved,
    )

    positive_market_count = sum(
        to_decimal(row["market_expectancy"]) > 0
        for row in ranking
    )
    positive_execution_count = sum(
        to_decimal(row["execution_expectancy"]) > 0
        for row in ranking
    )
    positive_net_count = sum(
        to_decimal(row["net_expectancy"]) > 0
        for row in ranking
    )

    best_execution_expectancy = (
        max(
            to_decimal(row["execution_expectancy"])
            for row in ranking
        )
        if ranking
        else Decimal("0")
    )

    contract = (
        "POSTGRESQL EXECUTION EDGE RUN RANKING V1",
        "========================================",
        "",
        f"BATCH_ID={args.batch_id}",
        f"STRATEGY={TARGET_STRATEGY}",
        f"SYMBOL={TARGET_SYMBOL}",
        f"TIMEFRAME={TARGET_TIMEFRAME}",
        f"RUN_COUNT={len(ranking)}",
        f"POSITIVE_MARKET_RUN_COUNT={positive_market_count}",
        (
            "POSITIVE_EXECUTION_RUN_COUNT="
            f"{positive_execution_count}"
        ),
        f"POSITIVE_NET_RUN_COUNT={positive_net_count}",
        (
            "BEST_EXECUTION_EXPECTANCY="
            f"{best_execution_expectancy}"
        ),
        f"UNRESOLVED_COUNT={len(unresolved)}",
        "DATABASE=POSTGRESQL_ONLY",
        "DB_WRITES_PERFORMED=0",
        "RUNTIME_CHANGED=0",
        "EXECUTION_CHANGED=0",
        "ORDERS_CHANGED=0",
        "FILLS_CHANGED=0",
        "OOS_ALLOWED=0",
        "SHADOW_ALLOWED=0",
        "PAPER_ALLOWED=0",
        "MICRO_LIVE_ALLOWED=0",
    )

    (output_dir / "contract.txt").write_text(
        "\n".join(contract) + "\n",
        encoding="utf-8",
    )

    print("=== POSTGRESQL EXECUTION EDGE RUN RANKING V1 ===")
    print(f"batch_id={args.batch_id}")
    print(f"run_count={len(ranking)}")
    print(
        f"positive_market_run_count="
        f"{positive_market_count}"
    )
    print(
        f"positive_execution_run_count="
        f"{positive_execution_count}"
    )
    print(f"positive_net_run_count={positive_net_count}")
    print(
        f"best_execution_expectancy="
        f"{best_execution_expectancy}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in ranking[:10]:
        print(
            "RUN_RANK "
            f"rank={row['rank']} "
            f"run_uuid={row['run_uuid']} "
            f"trades={row['trades']} "
            f"market_expectancy="
            f"{row['market_expectancy']} "
            f"execution_expectancy="
            f"{row['execution_expectancy']} "
            f"net_expectancy={row['net_expectancy']} "
            f"break_even_commission="
            f"{row['break_even_round_trip_commission']} "
            f"classification={row['classification']} "
            f"parameter_hash={row['parameter_hash']}"
        )

    print("db_writes_performed=0")
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
        "POSTGRESQL_EXECUTION_EDGE_RUN_RANKING_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
