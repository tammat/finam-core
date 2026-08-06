#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


EXPECTED_STRATEGIES = {
    "ATR_IMPULSE_V1",
    "MOMENTUM_CONTINUATION_V1",
}

EXPECTED_SYMBOLS = {
    "LKOH@MISX",
    "SBER@MISX",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверка результата PostgreSQL Edge Parameter Search V1"
    )
    parser.add_argument("--batch-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    count(*)::bigint AS task_count,
                    count(*) FILTER (
                        WHERE r.status_code = 'DONE'
                    )::bigint AS done_count,
                    count(*) FILTER (
                        WHERE r.status_code = 'QUEUED'
                    )::bigint AS queued_count,
                    count(*) FILTER (
                        WHERE r.status_code = 'FAILED'
                    )::bigint AS failed_count,
                    count(*) FILTER (
                        WHERE o.expectancy > 0
                          AND o.profit_factor > 1
                          AND o.trades >= 30
                          AND o.commission > 0
                          AND o.slippage > 0
                    )::bigint AS candidate_count,
                    min(o.expectancy)::numeric AS min_expectancy,
                    max(o.expectancy)::numeric AS max_expectancy,
                    min(o.profit_factor)::numeric AS min_profit_factor,
                    max(o.profit_factor)::numeric AS max_profit_factor,
                    count(DISTINCT r.strategy_code)::bigint
                        AS strategy_count,
                    count(DISTINCT r.symbol)::bigint
                        AS symbol_count,
                    count(DISTINCT r.timeframe)::bigint
                        AS timeframe_count
                FROM analytics.edge_lab_run_v1 r
                LEFT JOIN analytics.edge_observation_v1 o
                  ON o.run_uuid = r.run_uuid
                WHERE r.research_batch_id = %s
                """,
                (args.batch_id,),
            )
            summary = cur.fetchone()

            cur.execute(
                """
                SELECT DISTINCT strategy_code
                FROM analytics.edge_lab_run_v1
                WHERE research_batch_id = %s
                ORDER BY strategy_code
                """,
                (args.batch_id,),
            )
            strategies = {
                str(row["strategy_code"])
                for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT DISTINCT symbol
                FROM analytics.edge_lab_run_v1
                WHERE research_batch_id = %s
                ORDER BY symbol
                """,
                (args.batch_id,),
            )
            symbols = {
                str(row["symbol"])
                for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT
                    r.strategy_code,
                    r.symbol,
                    count(*)::bigint AS run_count,
                    max(o.expectancy)::numeric AS best_expectancy,
                    max(o.profit_factor)::numeric AS best_profit_factor
                FROM analytics.edge_lab_run_v1 r
                JOIN analytics.edge_observation_v1 o
                  ON o.run_uuid = r.run_uuid
                WHERE r.research_batch_id = %s
                GROUP BY r.strategy_code, r.symbol
                ORDER BY r.strategy_code, r.symbol
                """,
                (args.batch_id,),
            )
            groups = cur.fetchall()

    assert int(summary["task_count"]) == 72
    assert int(summary["done_count"]) == 72
    assert int(summary["queued_count"]) == 0
    assert int(summary["failed_count"]) == 0
    assert int(summary["candidate_count"]) == 0
    assert strategies == EXPECTED_STRATEGIES
    assert symbols == EXPECTED_SYMBOLS
    assert int(summary["timeframe_count"]) == 1
    assert Decimal(summary["max_expectancy"]) < 0
    assert Decimal(summary["max_profit_factor"]) < 1

    print(f"batch_id={args.batch_id}")
    print(f"task_count={summary['task_count']}")
    print(f"done_count={summary['done_count']}")
    print(f"candidate_count={summary['candidate_count']}")
    print(f"best_expectancy={summary['max_expectancy']}")
    print(f"best_profit_factor={summary['max_profit_factor']}")

    for row in groups:
        print(
            "STRATEGY_GROUP "
            f"strategy={row['strategy_code']} "
            f"symbol={row['symbol']} "
            f"runs={row['run_count']} "
            f"best_expectancy={row['best_expectancy']} "
            f"best_profit_factor={row['best_profit_factor']}"
        )

    print("strategy_family_atr_impulse_rejected_in_scope=1")
    print("strategy_family_momentum_continuation_rejected_in_scope=1")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_PARAMETER_SEARCH_V1_NO_EDGE_CONFIRMED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
