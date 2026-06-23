#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

PRIMARY_SYMBOLS = ("NGM6@RTSX", "NGN6@RTSX", "GDU6@RTSX", "GLU6@RTSX")
TABLE = "analytics_futures_rs_bottom_paper_observation_v1"

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_RUNTIME_DRY_RUN_V1_PLAN ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")
    print("strategy=RS_BOTTOM_RUNTIME_DRY_RUN_V1")
    print("selection=BOTTOM3")
    print("filter_name=COMPRESSION_RANGE")
    print("excluded_hours_msk=12,13,14")
    print("symbols=" + ",".join(PRIMARY_SYMBOLS))

    sql = f"""
        with src as (
            select
                symbol,
                family,
                source_ts,
                source_close,
                future_ts,
                future_close,
                return_pct,
                status,
                extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
            from {TABLE}
            where symbol = any(%s)
              and selection = 'BOTTOM3'
              and filter_name = 'COMPRESSION_RANGE'
              and status in ('SUCCESS','FAILURE','WAITING')
              and source_ts is not null
              and extract(hour from source_ts at time zone 'Europe/Moscow')::int not in (12,13,14)
        )
        select
            symbol,
            coalesce(max(family), 'UNKNOWN') as family,
            count(*)::int as signals_total,
            count(*) filter (where status='SUCCESS')::int as success,
            count(*) filter (where status='FAILURE')::int as failure,
            count(*) filter (where status='WAITING')::int as waiting,
            count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
            avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as expectancy,
            case
                when abs(sum(least(return_pct, 0)) filter (where status in ('SUCCESS','FAILURE'))) > 0
                then
                    sum(greatest(return_pct, 0)) filter (where status in ('SUCCESS','FAILURE')
                    )
                    / abs(sum(least(return_pct, 0)) filter (where status in ('SUCCESS','FAILURE')))
                else null
            end as profit_factor,
            avg(case when status='SUCCESS' then 1.0 when status='FAILURE' then 0.0 else null end) as winrate,
            min(source_ts) as first_ts,
            max(source_ts) as last_ts
        from src
        group by symbol
        order by profit_factor desc nulls last, completed desc;
    """

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (list(PRIMARY_SYMBOLS),))
            rows = cur.fetchall()

    total_completed = 0
    confirmed = 0

    print("\nDRY_RUN_PLAN_ROWS")
    for r in rows:
        completed = int(r["completed"] or 0)
        pf = float(r["profit_factor"] or 0)
        expectancy = float(r["expectancy"] or 0)

        if completed >= 15 and pf >= 1.5 and expectancy > 0:
            decision = "ELIGIBLE_FOR_SHADOW_ACCUMULATION"
            confirmed += 1
        else:
            decision = "WATCH_ONLY"

        total_completed += completed

        print(
            f"DRY_RUN_PLAN_ROW symbol={r['symbol']} family={r['family']} "
            f"signals_total={r['signals_total']} completed={r['completed']} "
            f"success={r['success']} failure={r['failure']} waiting={r['waiting']} "
            f"expectancy={r['expectancy']} profit_factor={r['profit_factor']} "
            f"winrate={r['winrate']} first_ts={r['first_ts']} last_ts={r['last_ts']} "
            f"decision={decision}"
        )

    print("\nDRY_RUN_PLAN_STORAGE")
    print("target_table=analytics_rs_bottom_runtime_dry_run_v1")
    print("fields=symbol,family,signal_ts,entry_price,horizon_min,future_ts,future_price,return_pct,status,session_msk,created_at")
    print("apply_mode=next_step_only")
    print("orders_created=0")

    print("\nDRY_RUN_PLAN_SUMMARY")
    print(f"symbols_total={len(PRIMARY_SYMBOLS)}")
    print(f"rows_returned={len(rows)}")
    print(f"eligible_symbols={confirmed}")
    print(f"completed_total={total_completed}")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")

    if confirmed >= 2:
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_PLAN_READY")
    else:
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_PLAN_INSUFFICIENT")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
