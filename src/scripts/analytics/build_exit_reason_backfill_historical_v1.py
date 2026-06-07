#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2
import psycopg2.extras

JOIN_WINDOW_SECONDS = 180


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--window-seconds", type=int, default=JOIN_WINDOW_SECONDS)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    mode = "APPLY" if args.apply else "DRY_RUN"

    print("=== EXIT REASON BACKFILL HISTORICAL V1 ===")
    print(f"mode={mode}")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"join_window_seconds={args.window_seconds}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                WITH candidates AS (
                    SELECT
                        ct.id AS closed_trade_id,
                        ct.symbol,
                        ct.side,
                        ct.exit_ts,
                        ct.closed_at,
                        ct.created_at,
                        ct.payload AS closed_payload,
                        t.id AS trade_id,
                        t.fill_id,
                        t.ts AS trade_ts,
                        t.payload AS trade_payload,
                        COALESCE(
                            NULLIF(t.payload->>'reason', ''),
                            NULLIF(t.payload->>'exit_reason', ''),
                            NULLIF(t.payload->'features'->>'reason', ''),
                            NULLIF(t.payload->'features'->>'exit_reason', '')
                        ) AS exit_reason,
                        abs(extract(epoch from (
                            COALESCE(ct.exit_ts, ct.closed_at, ct.created_at) - t.ts
                        ))) AS delta_sec,
                        row_number() OVER (
                            PARTITION BY ct.id
                            ORDER BY abs(extract(epoch from (
                                COALESCE(ct.exit_ts, ct.closed_at, ct.created_at) - t.ts
                            ))) ASC, t.id DESC
                        ) AS rn
                    FROM closed_trades ct
                    JOIN trades t
                      ON t.symbol = ct.symbol
                     AND upper(t.side) <> upper(ct.side)
                     AND abs(extract(epoch from (
                         COALESCE(ct.exit_ts, ct.closed_at, ct.created_at) - t.ts
                     ))) <= %s
                    WHERE left(ct.symbol, 2) IN ('BR','NG')
                      AND nullif(ct.payload->>'exit_reason', '') IS NULL
                      AND COALESCE(
                            NULLIF(t.payload->>'reason', ''),
                            NULLIF(t.payload->>'exit_reason', ''),
                            NULLIF(t.payload->'features'->>'reason', ''),
                            NULLIF(t.payload->'features'->>'exit_reason', '')
                          ) IS NOT NULL
                )
                SELECT *
                FROM candidates
                WHERE rn = 1
                ORDER BY symbol, exit_ts, closed_trade_id
                """,
                (args.window_seconds,),
            )
            rows = cur.fetchall()

            print("MATCH_CANDIDATES")
            by_reason = {}
            for r in rows:
                key = (r["symbol"], r["exit_reason"])
                by_reason[key] = by_reason.get(key, 0) + 1

            for (symbol, reason), cnt in sorted(by_reason.items()):
                print(f"CANDIDATE_ROW symbol={symbol} exit_reason={reason} rows={cnt}")

            print()
            print("SAMPLE")
            for r in rows[:30]:
                print(
                    f"SAMPLE_ROW closed_trade_id={r['closed_trade_id']} "
                    f"symbol={r['symbol']} side={r['side']} "
                    f"exit_reason={r['exit_reason']} trade_id={r['trade_id']} "
                    f"fill_id={r['fill_id']} delta_sec={float(r['delta_sec']):.2f}"
                )

            applied = 0
            if args.apply and rows:
                cur.execute(
                    """
                    WITH candidates AS (
                        SELECT
                            ct.id AS closed_trade_id,
                            t.id AS trade_id,
                            t.fill_id,
                            t.ts AS trade_ts,
                            COALESCE(
                                NULLIF(t.payload->>'reason', ''),
                                NULLIF(t.payload->>'exit_reason', ''),
                                NULLIF(t.payload->'features'->>'reason', ''),
                                NULLIF(t.payload->'features'->>'exit_reason', '')
                            ) AS exit_reason,
                            abs(extract(epoch from (
                                COALESCE(ct.exit_ts, ct.closed_at, ct.created_at) - t.ts
                            ))) AS delta_sec,
                            row_number() OVER (
                                PARTITION BY ct.id
                                ORDER BY abs(extract(epoch from (
                                    COALESCE(ct.exit_ts, ct.closed_at, ct.created_at) - t.ts
                                ))) ASC, t.id DESC
                            ) AS rn
                        FROM closed_trades ct
                        JOIN trades t
                          ON t.symbol = ct.symbol
                         AND upper(t.side) <> upper(ct.side)
                         AND abs(extract(epoch from (
                             COALESCE(ct.exit_ts, ct.closed_at, ct.created_at) - t.ts
                         ))) <= %s
                        WHERE left(ct.symbol, 2) IN ('BR','NG')
                          AND nullif(ct.payload->>'exit_reason', '') IS NULL
                          AND COALESCE(
                                NULLIF(t.payload->>'reason', ''),
                                NULLIF(t.payload->>'exit_reason', ''),
                                NULLIF(t.payload->'features'->>'reason', ''),
                                NULLIF(t.payload->'features'->>'exit_reason', '')
                              ) IS NOT NULL
                    ),
                    selected AS (
                        SELECT *
                        FROM candidates
                        WHERE rn = 1
                    ),
                    updated AS (
                        UPDATE closed_trades ct
                        SET payload =
                            COALESCE(ct.payload, '{}'::jsonb)
                            || jsonb_build_object(
                                'exit_reason', selected.exit_reason,
                                'exit_reason_source', 'exit_reason_backfill_historical_v1',
                                'exit_trade_id', selected.trade_id,
                                'exit_fill_id', selected.fill_id,
                                'exit_reason_event_ts', selected.trade_ts::text,
                                'exit_reason_join_delta_sec', selected.delta_sec
                            )
                        FROM selected
                        WHERE ct.id = selected.closed_trade_id
                        RETURNING ct.id
                    )
                    SELECT count(*) AS applied
                    FROM updated
                    """,
                    (args.window_seconds,),
                )
                applied = int(cur.fetchone()["applied"] or 0)

        print()
        print("SUMMARY")
        print(f"TOTAL_CANDIDATES={len(rows)}")
        print(f"APPLIED_ROWS={applied}")
        print(f"VERDICT={'APPLIED' if args.apply else 'DRY_RUN_ONLY'}")
        print("EXIT_REASON_BACKFILL_HISTORICAL_V1_OK")


if __name__ == "__main__":
    main()
