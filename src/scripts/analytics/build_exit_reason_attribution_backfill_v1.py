#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2
import psycopg2.extras


JOIN_WINDOW_SECONDS = 180


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL_NOT_SET")
    return url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--window-sec", type=int, default=JOIN_WINDOW_SECONDS)
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY_RUN"

    print("=== EXIT REASON ATTRIBUTION BACKFILL V1 ===")
    print(f"mode={mode}")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"join_window_seconds={args.window_sec}")
    print()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

            print("MATCH_CANDIDATES")
            cur.execute(
                """
                WITH exit_events AS (
                    SELECT
                        id AS trade_id,
                        symbol,
                        upper(side) AS exit_side,
                        ts AS exit_event_ts,
                        coalesce(
                            payload->>'reason',
                            payload->'features'->>'reason',
                            payload->>'exit_reason',
                            payload->'features'->>'exit_reason',
                            'UNKNOWN'
                        ) AS exit_reason,
                        fill_id
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
                ),
                joined AS (
                    SELECT
                        ct.id AS closed_trade_id,
                        ct.symbol,
                        upper(ct.side) AS closed_side,
                        ct.net_pnl,
                        coalesce(ct.exit_ts, ct.closed_at, ct.created_at) AS closed_exit_ts,
                        ee.trade_id AS exit_trade_id,
                        ee.exit_reason,
                        ee.exit_event_ts,
                        ee.fill_id AS exit_fill_id,
                        abs(extract(epoch FROM (
                            coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                        ))) AS join_delta_sec,
                        row_number() OVER (
                            PARTITION BY ct.id
                            ORDER BY abs(extract(epoch FROM (
                                coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                            ))) ASC
                        ) AS rn
                    FROM closed_trades ct
                    JOIN exit_events ee
                      ON ee.symbol = ct.symbol
                     AND abs(extract(epoch FROM (
                         coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                     ))) <= %s
                    WHERE left(ct.symbol, 2) IN ('BR','NG')
                      AND coalesce(ct.payload->>'exit_reason','') = ''
                ),
                best AS (
                    SELECT *
                    FROM joined
                    WHERE rn = 1
                )
                SELECT
                    symbol,
                    exit_reason,
                    count(*) AS rows,
                    min(closed_exit_ts) AS first_closed_exit_ts,
                    max(closed_exit_ts) AS last_closed_exit_ts,
                    round(avg(join_delta_sec)::numeric, 2) AS avg_join_delta_sec
                FROM best
                GROUP BY 1,2
                ORDER BY symbol, rows DESC, exit_reason;
                """,
                (args.window_sec,),
            )

            candidates = cur.fetchall()
            total_candidates = sum(int(r["rows"]) for r in candidates)

            if candidates:
                for r in candidates:
                    print(
                        f"CANDIDATE_ROW symbol={r['symbol']} exit_reason={r['exit_reason']} "
                        f"rows={r['rows']} first_closed_exit_ts={r['first_closed_exit_ts']} "
                        f"last_closed_exit_ts={r['last_closed_exit_ts']} "
                        f"avg_join_delta_sec={r['avg_join_delta_sec']}"
                    )
            else:
                print("NO_MATCH_CANDIDATES")
            print()

            print("SUMMARY")
            print(f"TOTAL_CANDIDATES={total_candidates}")

            if not args.apply:
                print("APPLIED_ROWS=0")
                print("VERDICT=DRY_RUN_ONLY")
                print("EXIT_REASON_ATTRIBUTION_BACKFILL_V1_OK")
                return

            cur.execute(
                """
                WITH exit_events AS (
                    SELECT
                        id AS trade_id,
                        symbol,
                        ts AS exit_event_ts,
                        coalesce(
                            payload->>'reason',
                            payload->'features'->>'reason',
                            payload->>'exit_reason',
                            payload->'features'->>'exit_reason',
                            'UNKNOWN'
                        ) AS exit_reason,
                        fill_id
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
                ),
                joined AS (
                    SELECT
                        ct.id AS closed_trade_id,
                        ee.trade_id AS exit_trade_id,
                        ee.exit_reason,
                        ee.exit_event_ts,
                        ee.fill_id AS exit_fill_id,
                        abs(extract(epoch FROM (
                            coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                        ))) AS join_delta_sec,
                        row_number() OVER (
                            PARTITION BY ct.id
                            ORDER BY abs(extract(epoch FROM (
                                coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                            ))) ASC
                        ) AS rn
                    FROM closed_trades ct
                    JOIN exit_events ee
                      ON ee.symbol = ct.symbol
                     AND abs(extract(epoch FROM (
                         coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                     ))) <= %s
                    WHERE left(ct.symbol, 2) IN ('BR','NG')
                      AND coalesce(ct.payload->>'exit_reason','') = ''
                ),
                best AS (
                    SELECT *
                    FROM joined
                    WHERE rn = 1
                ),
                updated AS (
                    UPDATE closed_trades ct
                    SET payload =
                        coalesce(ct.payload, '{}'::jsonb)
                        || jsonb_build_object(
                            'exit_reason', best.exit_reason,
                            'exit_trade_id', best.exit_trade_id,
                            'exit_fill_id', best.exit_fill_id,
                            'exit_reason_source', 'exit_reason_attribution_backfill_v1',
                            'exit_reason_join_delta_sec', best.join_delta_sec,
                            'exit_reason_event_ts', best.exit_event_ts
                        )
                    FROM best
                    WHERE ct.id = best.closed_trade_id
                    RETURNING ct.id
                )
                SELECT count(*) AS applied_rows
                FROM updated;
                """,
                (args.window_sec,),
            )

            applied = int(cur.fetchone()["applied_rows"])
            conn.commit()

            print(f"APPLIED_ROWS={applied}")
            print("VERDICT=APPLIED")
            print("EXIT_REASON_ATTRIBUTION_BACKFILL_V1_OK")


if __name__ == "__main__":
    main()
