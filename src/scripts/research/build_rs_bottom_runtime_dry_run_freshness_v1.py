#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

TABLE = "analytics_rs_bottom_runtime_dry_run_v1"
STRATEGY = "RS_BOTTOM_RUNTIME_DRY_RUN_V1"
SYMBOLS = ("GDU6@RTSX", "GLU6@RTSX", "NGM6@RTSX")
FRESH_MINUTES = 90

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_RUNTIME_DRY_RUN_FRESHNESS_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")
    print(f"source_table={TABLE}")
    print(f"fresh_minutes={FRESH_MINUTES}")

    sql = f"""
        select
            symbol,
            max(signal_ts) as last_signal_ts,
            max(created_at) as last_created_at,
            count(*)::int as rows_total,
            count(*) filter (
                where created_at >= now() - (%s::text || ' minutes')::interval
            )::int as fresh_created_rows,
            count(*) filter (
                where status='WAITING'
            )::int as waiting_rows,
            count(*) filter (
                where status in ('SUCCESS','FAILURE')
            )::int as completed_rows
        from {TABLE}
        where strategy=%s
          and symbol = any(%s)
          and horizon_min=240
          and selection='BOTTOM3'
          and filter_name='COMPRESSION_RANGE'
        group by symbol
        order by symbol
    """

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (FRESH_MINUTES, STRATEGY, list(SYMBOLS)))
            rows = cur.fetchall()

    print("\nFRESHNESS_ROWS")

    fresh_count = 0
    stale_count = 0

    for r in rows:
        fresh_rows = int(r["fresh_created_rows"] or 0)
        waiting_rows = int(r["waiting_rows"] or 0)

        if fresh_rows > 0 or waiting_rows > 0:
            status = "FRESH_OR_WAITING"
            fresh_count += 1
        else:
            status = "STALE"
            stale_count += 1

        print(
            f"FRESHNESS_ROW symbol={r['symbol']} "
            f"rows_total={r['rows_total']} completed_rows={r['completed_rows']} "
            f"waiting_rows={r['waiting_rows']} fresh_created_rows={r['fresh_created_rows']} "
            f"last_signal_ts={r['last_signal_ts']} last_created_at={r['last_created_at']} "
            f"freshness_status={status}"
        )

    print("\nFRESHNESS_SUMMARY")
    print(f"symbols_total={len(SYMBOLS)}")
    print(f"rows_returned={len(rows)}")
    print(f"fresh_or_waiting_symbols={fresh_count}")
    print(f"stale_symbols={stale_count}")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")

    if len(rows) == len(SYMBOLS) and fresh_count > 0:
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_FRESHNESS_HAS_ACTIVE_ROWS")
    elif len(rows) == len(SYMBOLS):
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_FRESHNESS_STALE")
    else:
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_FRESHNESS_INCOMPLETE")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
