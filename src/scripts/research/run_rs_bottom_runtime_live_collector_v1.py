#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg

SOURCE_TABLE = "analytics_futures_rs_bottom_paper_observation_v1"
TARGET_TABLE = "analytics_rs_bottom_runtime_dry_run_v1"

STRATEGY = "RS_BOTTOM_RUNTIME_DRY_RUN_V1"
SYMBOLS = ("GDU6@RTSX", "GLU6@RTSX", "NGM6@RTSX")
SELECTION = "BOTTOM3"
FILTER_NAME = "COMPRESSION_RANGE"
HORIZON_MIN = 240

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_V1 ===")
    print("mode=shadow_live_collect")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")
    print(f"source_table={SOURCE_TABLE}")
    print(f"target_table={TARGET_TABLE}")
    print("symbols=" + ",".join(SYMBOLS))

    sql = f"""
        insert into {TARGET_TABLE} (
            strategy, mode, symbol, family, signal_ts, session_msk,
            selection, filter_name, entry_price, horizon_min,
            future_ts, future_price, return_pct, status,
            runtime_allow_trading, execution_enabled, real_trading_enabled, paper_orders,
            source_table, source_id, payload
        )
        select
            %s,
            'SHADOW',
            src.symbol,
            coalesce(src.family, 'UNKNOWN'),
            src.source_ts,
            extract(hour from src.source_ts at time zone 'Europe/Moscow')::int,
            src.selection,
            src.filter_name,
            src.source_close,
            src.horizon_min,
            src.future_ts,
            src.future_close,
            src.return_pct,
            src.status,
            false,
            false,
            false,
            false,
            %s,
            src.id,
            jsonb_build_object(
                'source', %s::text,
                'collector_version', 'RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_V1',
                'collector_mode', 'shadow_live_collect'
            )
        from {SOURCE_TABLE} src
        where src.symbol = any(%s)
          and src.selection = %s
          and src.filter_name = %s
          and src.horizon_min = %s
          and src.status in ('SUCCESS','FAILURE','WAITING')
          and src.source_ts is not null
          and extract(hour from src.source_ts at time zone 'Europe/Moscow')::int not in (12,13,14)
          and src.source_ts >= now() - interval '36 hours'
        on conflict (symbol, signal_ts, horizon_min, selection, filter_name)
        do update set
            future_ts = excluded.future_ts,
            future_price = excluded.future_price,
            return_pct = excluded.return_pct,
            status = excluded.status,
            payload = {TARGET_TABLE}.payload || excluded.payload
    """

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                STRATEGY,
                SOURCE_TABLE,
                SOURCE_TABLE,
                list(SYMBOLS),
                SELECTION,
                FILTER_NAME,
                HORIZON_MIN,
            ))
            affected = cur.rowcount
            conn.commit()

            cur.execute(f"""
                select
                    symbol,
                    count(*)::int as rows_total,
                    count(*) filter (where status='WAITING')::int as waiting,
                    count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                    max(signal_ts) as last_signal_ts,
                    max(created_at) as last_created_at,
                    count(*) filter (where runtime_allow_trading=false)::int as runtime_blocked,
                    count(*) filter (where execution_enabled=false)::int as execution_blocked,
                    count(*) filter (where real_trading_enabled=false)::int as real_blocked,
                    count(*) filter (where paper_orders=false)::int as paper_blocked
                from {TARGET_TABLE}
                where strategy=%s
                  and symbol = any(%s)
                  and selection=%s
                  and filter_name=%s
                  and horizon_min=%s
                group by symbol
                order by symbol
            """, (STRATEGY, list(SYMBOLS), SELECTION, FILTER_NAME, HORIZON_MIN))
            rows = cur.fetchall()

    unsafe = 0

    print("\nCOLLECTOR_ROWS")
    for r in rows:
        (
            symbol, rows_total, waiting, completed,
            last_signal_ts, last_created_at,
            runtime_blocked, execution_blocked, real_blocked, paper_blocked
        ) = r

        if not (
            runtime_blocked == rows_total
            and execution_blocked == rows_total
            and real_blocked == rows_total
            and paper_blocked == rows_total
        ):
            unsafe += 1

        print(
            f"COLLECTOR_ROW symbol={symbol} rows_total={rows_total} "
            f"completed={completed} waiting={waiting} "
            f"last_signal_ts={last_signal_ts} last_created_at={last_created_at} "
            f"runtime_blocked={runtime_blocked} execution_blocked={execution_blocked} "
            f"real_blocked={real_blocked} paper_blocked={paper_blocked}"
        )

    print("\nCOLLECTOR_SUMMARY")
    print(f"affected_rows={affected}")
    print(f"symbols_total={len(SYMBOLS)}")
    print(f"rows_returned={len(rows)}")
    print(f"unsafe_symbols={unsafe}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")

    if len(rows) == len(SYMBOLS) and unsafe == 0:
        print("VERDICT=RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_OK")
        return 0

    print("VERDICT=RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_FAILED")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
