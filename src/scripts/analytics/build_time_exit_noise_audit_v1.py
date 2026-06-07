#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL_NOT_SET")
    return url


def main() -> None:
    print("=== TIME EXIT NOISE AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

            print("CLOSED_TRADE_QUALITY_BY_ROOT_SIDE")
            cur.execute("""
                SELECT
                    coalesce(root_symbol,
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END
                    ) AS root,
                    upper(side) AS side,
                    count(*) AS trades,
                    count(*) FILTER (WHERE net_pnl > 0) AS wins,
                    count(*) FILTER (WHERE net_pnl < 0) AS losses,
                    round(sum(net_pnl)::numeric, 6) AS net_pnl,
                    round(avg(net_pnl)::numeric, 6) AS expectancy,
                    CASE
                        WHEN abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) > 0
                        THEN round(
                            (sum(net_pnl) FILTER (WHERE net_pnl > 0))::numeric
                            / abs((sum(net_pnl) FILTER (WHERE net_pnl < 0))::numeric),
                            6
                        )
                        ELSE NULL
                    END AS profit_factor,
                    round(avg(coalesce(holding_seconds, hold_seconds, 0))::numeric, 2) AS avg_hold_sec
                FROM closed_trades
                WHERE left(symbol, 2) IN ('BR','NG')
                GROUP BY 1,2
                ORDER BY 1,2;
            """)
            for r in cur.fetchall():
                print(
                    f"QUALITY_ROW root={r['root']} side={r['side']} "
                    f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
                    f"net_pnl={r['net_pnl']} expectancy={r['expectancy']} "
                    f"profit_factor={r['profit_factor']} avg_hold_sec={r['avg_hold_sec']}"
                )
            print()

            print("EXIT_EVENT_REASON_SUMMARY_FROM_TRADES")
            cur.execute("""
                WITH exit_events AS (
                    SELECT
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        symbol,
                        upper(side) AS side,
                        coalesce(
                            payload->>'reason',
                            payload->'features'->>'reason',
                            payload->>'exit_reason',
                            payload->'features'->>'exit_reason',
                            'UNKNOWN'
                        ) AS reason,
                        ts,
                        price,
                        qty,
                        payload
                    FROM trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                      AND coalesce(is_invalid,false)=false
                      AND (
                            payload->>'intent_type' = 'EXIT'
                         OR payload->'features'->>'is_exit' = 'True'
                         OR payload->'features'->>'is_exit' = 'true'
                         OR coalesce(payload->>'reason','') IN ('time_exit','stop_loss_long','stop_loss_short','take_profit_long','take_profit_short')
                         OR coalesce(payload->'features'->>'reason','') IN ('time_exit','stop_loss_long','stop_loss_short','take_profit_long','take_profit_short')
                      )
                )
                SELECT
                    root,
                    symbol,
                    reason,
                    count(*) AS rows,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM exit_events
                GROUP BY 1,2,3
                ORDER BY root, symbol, rows DESC, reason;
            """)
            for r in cur.fetchall():
                print(
                    f"EXIT_REASON_ROW root={r['root']} symbol={r['symbol']} "
                    f"reason={str(r['reason']).replace(' ', '_')} rows={r['rows']} "
                    f"first_ts={r['first_ts']} last_ts={r['last_ts']}"
                )
            print()

            print("TIME_EXIT_ANALYSIS")
            cur.execute("""
                WITH exit_events AS (
                    SELECT
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        symbol,
                        upper(side) AS side,
                        coalesce(
                            payload->>'reason',
                            payload->'features'->>'reason',
                            payload->>'exit_reason',
                            payload->'features'->>'exit_reason',
                            'UNKNOWN'
                        ) AS reason,
                        ts
                    FROM trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                      AND coalesce(is_invalid,false)=false
                      AND (
                            payload->>'intent_type' = 'EXIT'
                         OR payload->'features'->>'is_exit' = 'True'
                         OR payload->'features'->>'is_exit' = 'true'
                      )
                )
                SELECT
                    root,
                    CASE WHEN reason = 'time_exit' THEN 'TIME_EXIT' ELSE 'OTHER_EXIT' END AS exit_bucket,
                    count(*) AS rows,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM exit_events
                GROUP BY 1,2
                ORDER BY root, exit_bucket;
            """)
            for r in cur.fetchall():
                print(
                    f"TIME_EXIT_ROW root={r['root']} bucket={r['exit_bucket']} "
                    f"rows={r['rows']} first_ts={r['first_ts']} last_ts={r['last_ts']}"
                )
            print()

            print("TIME_EXIT_DUPLICATE_AUDIT")
            cur.execute("""
                WITH exit_events AS (
                    SELECT
                        symbol,
                        upper(side) AS side,
                        coalesce(
                            payload->>'reason',
                            payload->'features'->>'reason',
                            payload->>'exit_reason',
                            payload->'features'->>'exit_reason',
                            'UNKNOWN'
                        ) AS reason,
                        ts,
                        lag(ts) OVER (
                            PARTITION BY symbol, upper(side),
                            coalesce(
                                payload->>'reason',
                                payload->'features'->>'reason',
                                payload->>'exit_reason',
                                payload->'features'->>'exit_reason',
                                'UNKNOWN'
                            )
                            ORDER BY ts
                        ) AS prev_ts
                    FROM trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                      AND coalesce(is_invalid,false)=false
                      AND (
                            payload->>'intent_type' = 'EXIT'
                         OR payload->'features'->>'is_exit' = 'True'
                         OR payload->'features'->>'is_exit' = 'true'
                      )
                ),
                dup AS (
                    SELECT *
                    FROM exit_events
                    WHERE reason = 'time_exit'
                      AND prev_ts IS NOT NULL
                      AND extract(epoch FROM (ts - prev_ts)) BETWEEN 0 AND 60
                )
                SELECT
                    symbol,
                    side,
                    reason,
                    count(*) AS duplicates,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM dup
                GROUP BY 1,2,3
                ORDER BY duplicates DESC;
            """)
            dup_rows = cur.fetchall()
            if dup_rows:
                for r in dup_rows:
                    print(
                        f"DUPLICATE_ROW symbol={r['symbol']} side={r['side']} "
                        f"reason={r['reason']} duplicates={r['duplicates']} "
                        f"first_ts={r['first_ts']} last_ts={r['last_ts']}"
                    )
            else:
                print("NO_TIME_EXIT_DUPLICATES_WITHIN_60_SEC")
            print()

            print("VERDICT=TIME_EXIT_NOISE_AUDIT_RECORDED")
            print("TIME_EXIT_NOISE_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
