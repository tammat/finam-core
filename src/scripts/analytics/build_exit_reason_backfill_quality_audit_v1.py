#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SOURCE = "exit_reason_backfill_historical_v1"


def main() -> None:
    print("=== EXIT REASON BACKFILL QUALITY AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"backfill_source={SOURCE}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            print("BACKFILL_ROWS")
            cur.execute("""
                SELECT
                    left(symbol, 2) AS root,
                    count(*) AS rows
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                GROUP BY 1
                ORDER BY 1
            """, (SOURCE,))
            for r in cur.fetchall():
                print(f"BACKFILL_ROW root={r['root']} rows={r['rows']}")
            print()

            print("DUPLICATE_EXIT_TRADE_ID")
            cur.execute("""
                SELECT
                    payload->>'exit_trade_id' AS exit_trade_id,
                    count(*) AS rows,
                    min(id) AS min_closed_trade_id,
                    max(id) AS max_closed_trade_id
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                  AND nullif(payload->>'exit_trade_id', '') IS NOT NULL
                GROUP BY 1
                HAVING count(*) > 1
                ORDER BY rows DESC, exit_trade_id
                LIMIT 50
            """, (SOURCE,))
            dup_trade = cur.fetchall()
            if not dup_trade:
                print("NONE")
            for r in dup_trade:
                print(
                    f"DUP_EXIT_TRADE_ROW exit_trade_id={r['exit_trade_id']} "
                    f"rows={r['rows']} min_closed_trade_id={r['min_closed_trade_id']} "
                    f"max_closed_trade_id={r['max_closed_trade_id']}"
                )
            print()

            print("DUPLICATE_EXIT_FILL_ID")
            cur.execute("""
                SELECT
                    payload->>'exit_fill_id' AS exit_fill_id,
                    count(*) AS rows,
                    min(id) AS min_closed_trade_id,
                    max(id) AS max_closed_trade_id
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                  AND nullif(payload->>'exit_fill_id', '') IS NOT NULL
                GROUP BY 1
                HAVING count(*) > 1
                ORDER BY rows DESC, exit_fill_id
                LIMIT 50
            """, (SOURCE,))
            dup_fill = cur.fetchall()
            if not dup_fill:
                print("NONE")
            for r in dup_fill:
                print(
                    f"DUP_EXIT_FILL_ROW exit_fill_id={r['exit_fill_id']} "
                    f"rows={r['rows']} min_closed_trade_id={r['min_closed_trade_id']} "
                    f"max_closed_trade_id={r['max_closed_trade_id']}"
                )
            print()

            print("JOIN_DELTA_AUDIT")
            cur.execute("""
                SELECT
                    left(symbol, 2) AS root,
                    count(*) AS rows,
                    max((payload->>'exit_reason_join_delta_sec')::numeric) AS max_delta_sec,
                    avg((payload->>'exit_reason_join_delta_sec')::numeric) AS avg_delta_sec,
                    count(*) FILTER (
                        WHERE (payload->>'exit_reason_join_delta_sec')::numeric > 5
                    ) AS rows_gt_5_sec,
                    count(*) FILTER (
                        WHERE (payload->>'exit_reason_join_delta_sec')::numeric > 60
                    ) AS rows_gt_60_sec
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                  AND nullif(payload->>'exit_reason_join_delta_sec', '') IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """, (SOURCE,))
            for r in cur.fetchall():
                print(
                    f"DELTA_ROW root={r['root']} rows={r['rows']} "
                    f"max_delta_sec={float(r['max_delta_sec'] or 0):.2f} "
                    f"avg_delta_sec={float(r['avg_delta_sec'] or 0):.2f} "
                    f"rows_gt_5_sec={r['rows_gt_5_sec']} "
                    f"rows_gt_60_sec={r['rows_gt_60_sec']}"
                )
            print()

            print("SUSPICIOUS_REASON_AUDIT")
            cur.execute("""
                SELECT
                    left(symbol, 2) AS root,
                    symbol,
                    payload->>'exit_reason' AS exit_reason,
                    count(*) AS rows
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                  AND (
                        payload->>'exit_reason' ILIKE '%%breakout%%'
                     OR payload->>'exit_reason' ILIKE '%%smart_entry%%'
                     OR payload->>'exit_reason' ILIKE '%%entry%%'
                  )
                GROUP BY 1,2,3
                ORDER BY rows DESC, root, symbol
                LIMIT 100
            """, (SOURCE,))
            suspicious = cur.fetchall()
            if not suspicious:
                print("NONE")
            for r in suspicious:
                print(
                    f"SUSPICIOUS_REASON_ROW root={r['root']} symbol={r['symbol']} "
                    f"exit_reason={r['exit_reason']} rows={r['rows']}"
                )
            print()

            print("REASON_DISTRIBUTION_BACKFILLED")
            cur.execute("""
                SELECT
                    left(symbol, 2) AS root,
                    payload->>'exit_reason' AS exit_reason,
                    count(*) AS rows
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                GROUP BY 1,2
                ORDER BY 1, rows DESC, 2
            """, (SOURCE,))
            for r in cur.fetchall():
                print(
                    f"REASON_ROW root={r['root']} exit_reason={r['exit_reason']} rows={r['rows']}"
                )
            print()

            print("SAMPLE_BAD_LINKS")
            cur.execute("""
                SELECT
                    id,
                    symbol,
                    side,
                    exit_ts,
                    payload->>'exit_reason' AS exit_reason,
                    payload->>'exit_trade_id' AS exit_trade_id,
                    payload->>'exit_fill_id' AS exit_fill_id,
                    payload->>'exit_reason_join_delta_sec' AS delta_sec
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                  AND (
                        payload->>'exit_reason' ILIKE '%%breakout%%'
                     OR payload->>'exit_reason' ILIKE '%%smart_entry%%'
                     OR payload->>'exit_reason' ILIKE '%%entry%%'
                     OR (payload->>'exit_reason_join_delta_sec')::numeric > 60
                  )
                ORDER BY symbol, exit_ts, id
                LIMIT 30
            """, (SOURCE,))
            sample = cur.fetchall()
            if not sample:
                print("NONE")
            for r in sample:
                print(
                    f"SAMPLE_ROW id={r['id']} symbol={r['symbol']} side={r['side']} "
                    f"exit_ts={r['exit_ts']} exit_reason={r['exit_reason']} "
                    f"exit_trade_id={r['exit_trade_id']} delta_sec={r['delta_sec']}"
                )
            print()

    dup_trade_count = len(dup_trade)
    dup_fill_count = len(dup_fill)
    suspicious_count = len(suspicious)

    if dup_trade_count or dup_fill_count or suspicious_count:
        verdict = "BACKFILL_QUALITY_RISK_FOUND"
    else:
        verdict = "BACKFILL_QUALITY_OK"

    print("SUMMARY")
    print(f"DUP_EXIT_TRADE_GROUPS={dup_trade_count}")
    print(f"DUP_EXIT_FILL_GROUPS={dup_fill_count}")
    print(f"SUSPICIOUS_REASON_GROUPS={suspicious_count}")
    print(f"VERDICT={verdict}")
    print("EXIT_REASON_BACKFILL_QUALITY_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
