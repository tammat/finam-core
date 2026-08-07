#!/usr/bin/env python3
from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    r.symbol,
                    r.strategy_code,
                    r.timeframe,
                    count(DISTINCT r.run_uuid)::bigint
                        AS run_count,
                    count(t.*)::bigint
                        AS trade_count,
                    max(r.finished_at) AS latest_finished_at,
                    max(
                        (
                            SELECT avg(
                                x.gross_pnl
                                - coalesce(x.slippage, 0)
                            )
                            FROM analytics.research_trade_v1 x
                            WHERE x.run_uuid = r.run_uuid
                        )
                    )::numeric AS best_execution_expectancy
                FROM analytics.edge_lab_run_v1 r
                LEFT JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                WHERE
                    r.symbol LIKE 'BR%@RTSX'
                    OR r.symbol LIKE 'NG%@RTSX'
                    OR r.symbol LIKE '%RUBF@RTSX'
                GROUP BY
                    r.symbol,
                    r.strategy_code,
                    r.timeframe
                ORDER BY
                    r.symbol,
                    best_execution_expectancy DESC NULLS LAST,
                    trade_count DESC
                """
            )
            summary_rows = cur.fetchall()

            cur.execute(
                """
                SELECT
                    r.run_uuid::text,
                    r.research_batch_id,
                    r.research_code,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    r.status_code,
                    count(t.*)::bigint AS trades,
                    avg(
                        t.gross_pnl
                        - coalesce(t.slippage, 0)
                    )::numeric AS execution_expectancy,
                    sum(t.gross_pnl)::numeric AS gross_pnl,
                    sum(coalesce(t.slippage, 0))::numeric
                        AS slippage
                FROM analytics.edge_lab_run_v1 r
                JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                WHERE
                    (
                        r.symbol LIKE 'BR%@RTSX'
                        OR r.symbol LIKE 'NG%@RTSX'
                        OR r.symbol LIKE '%RUBF@RTSX'
                    )
                GROUP BY
                    r.run_uuid,
                    r.research_batch_id,
                    r.research_code,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    r.status_code
                HAVING count(t.*) >= 30
                ORDER BY
                    execution_expectancy DESC,
                    trades DESC,
                    r.run_uuid
                LIMIT 100
                """
            )
            candidate_rows = cur.fetchall()

    print("=== POSTGRESQL FUTURES REPLAY CANDIDATE DISCOVERY V1 ===")
    print(f"summary_row_count={len(summary_rows)}")
    print(f"candidate_run_count={len(candidate_rows)}")

    for row in summary_rows:
        print(
            "FUTURES_RUN_SUMMARY "
            f"symbol={row['symbol']} "
            f"strategy={row['strategy_code']} "
            f"timeframe={row['timeframe']} "
            f"runs={row['run_count']} "
            f"trades={row['trade_count']} "
            f"best_execution_expectancy="
            f"{row['best_execution_expectancy']} "
            f"latest_finished_at={row['latest_finished_at']}"
        )

    for row in candidate_rows:
        print(
            "FUTURES_REPLAY_CANDIDATE "
            f"run_uuid={row['run_uuid']} "
            f"batch={row['research_batch_id']} "
            f"strategy={row['strategy_code']} "
            f"symbol={row['symbol']} "
            f"timeframe={row['timeframe']} "
            f"status={row['status_code']} "
            f"trades={row['trades']} "
            f"execution_expectancy="
            f"{row['execution_expectancy']} "
            f"gross_pnl={row['gross_pnl']} "
            f"slippage={row['slippage']}"
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

    if not candidate_rows:
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_REPLAY_CANDIDATES_V1_NOT_FOUND"
        )
        return 2

    print(
        "VERDICT="
        "POSTGRESQL_FUTURES_REPLAY_CANDIDATES_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
