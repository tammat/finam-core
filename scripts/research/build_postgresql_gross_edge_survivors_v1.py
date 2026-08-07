#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import pathlib
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUTPUT_ROOT = pathlib.Path(
    "/tmp/postgresql_gross_edge_survivors_v1"
)


def write_tsv(
    path: pathlib.Path,
    rows: list[dict[str, Any]],
) -> None:
    fields = (
        "strategy_code",
        "symbol",
        "timeframe",
        "trades",
        "market_expectancy",
        "execution_expectancy",
        "net_expectancy",
        "slippage_per_trade",
        "commission_per_trade",
        "maximum_total_cost_per_trade",
        "maximum_commission_per_trade_after_slippage",
        "cost_headroom_status",
        "recommended_action",
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
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
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    count(*)::bigint AS trades,
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
                        AS commission_per_trade
                FROM analytics.edge_lab_run_v1 r
                JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                WHERE r.research_batch_id = %s
                GROUP BY
                    r.strategy_code,
                    r.symbol,
                    r.timeframe
                ORDER BY
                    market_expectancy DESC
                """,
                (args.batch_id,),
            )

            source_rows = cur.fetchall()

    result_rows: list[dict[str, Any]] = []

    for row in source_rows:
        market_expectancy = Decimal(
            row["market_expectancy"]
        )
        execution_expectancy = Decimal(
            row["execution_expectancy"]
        )
        net_expectancy = Decimal(
            row["net_expectancy"]
        )
        slippage = Decimal(row["slippage_per_trade"])

        maximum_total_cost = max(
            Decimal("0"),
            market_expectancy,
        )
        maximum_commission_after_slippage = max(
            Decimal("0"),
            execution_expectancy,
        )

        if market_expectancy <= 0:
            status = "NO_GROSS_EDGE"
            action = "REJECT_STRATEGY_SYMBOL"
        elif execution_expectancy <= 0:
            status = "SLIPPAGE_EXCEEDS_GROSS_EDGE"
            action = "REJECT_OR_CHANGE_EXECUTION_MODEL"
        elif net_expectancy <= 0:
            status = "COMMISSION_EXCEEDS_EDGE"
            action = "REDUCE_TURNOVER_OR_INCREASE_PAYOFF"
        else:
            status = "POSITIVE_AFTER_COSTS"
            action = "OOS_CANDIDATE"

        result_rows.append(
            {
                "strategy_code": row["strategy_code"],
                "symbol": row["symbol"],
                "timeframe": row["timeframe"],
                "trades": row["trades"],
                "market_expectancy": market_expectancy,
                "execution_expectancy": execution_expectancy,
                "net_expectancy": net_expectancy,
                "slippage_per_trade": slippage,
                "commission_per_trade": row[
                    "commission_per_trade"
                ],
                "maximum_total_cost_per_trade": (
                    maximum_total_cost
                ),
                "maximum_commission_per_trade_after_slippage": (
                    maximum_commission_after_slippage
                ),
                "cost_headroom_status": status,
                "recommended_action": action,
            }
        )

    write_tsv(
        output_dir / "gross_edge_survivors.tsv",
        result_rows,
    )

    survivor_count = sum(
        Decimal(row["market_expectancy"]) > 0
        for row in result_rows
    )
    execution_survivor_count = sum(
        Decimal(row["execution_expectancy"]) > 0
        for row in result_rows
    )
    net_survivor_count = sum(
        Decimal(row["net_expectancy"]) > 0
        for row in result_rows
    )

    print(f"batch_id={args.batch_id}")
    print(f"group_count={len(result_rows)}")
    print(f"gross_edge_survivor_count={survivor_count}")
    print(
        "execution_edge_survivor_count="
        f"{execution_survivor_count}"
    )
    print(f"net_edge_survivor_count={net_survivor_count}")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_GROSS_EDGE_SURVIVORS_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
