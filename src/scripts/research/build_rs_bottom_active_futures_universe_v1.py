#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

SELECTION = "BOTTOM3"
FILTER_NAME = "COMPRESSION_RANGE"
TABLE = "analytics_futures_rs_bottom_paper_observation_v1"

def classify(pf, completed):
    pf = float(pf or 0)
    completed = int(completed or 0)

    if completed < 10 and pf > 1.0:
        return "WATCH_ONLY"
    if completed >= 15 and pf >= 1.5:
        return "PRIMARY"
    if completed >= 15 and pf >= 1.0:
        return "SECONDARY"
    return "REJECT"

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_ACTIVE_FUTURES_UNIVERSE_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")

    sql = f"""
        with src as (
            select
                case
                    when left(symbol, 2) = 'BR' then 'BRENT_FUTURES'
                    when left(symbol, 2) = 'NG' then 'GAS_FUTURES'
                    when left(symbol, 2) in ('GD','GL') then 'GOLD_FUTURES'
                    when left(symbol, 7) = 'USDRUBF' then 'FX_FUTURES'
                    else 'OTHER'
                end as family,
                symbol,
                return_pct,
                status,
                source_ts
            from {TABLE}
            where selection = %s
              and filter_name = %s
              and status in ('SUCCESS','FAILURE')
              and return_pct is not null
              and extract(hour from source_ts at time zone 'Europe/Moscow')::int not in (12,13,14)
        )
        select
            family,
            symbol,
            count(*)::int as completed,
            count(*) filter (where status='SUCCESS')::int as success,
            count(*) filter (where status='FAILURE')::int as failure,
            avg(return_pct) as expectancy,
            case
                when abs(sum(least(return_pct, 0))) > 0
                then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                else null
            end as profit_factor,
            avg(case when status='SUCCESS' then 1.0 else 0.0 end) as winrate,
            min(source_ts) as first_ts,
            max(source_ts) as last_ts
        from src
        group by family, symbol
        order by family, profit_factor desc nulls last, completed desc
    """

    primary = []
    secondary = []
    watch = []
    reject = []

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (SELECTION, FILTER_NAME))
            rows = cur.fetchall()

    print("\nACTIVE_FUTURES_ROWS")
    for r in rows:
        status = classify(r["profit_factor"], r["completed"])
        symbol = r["symbol"]

        if status == "PRIMARY":
            primary.append(symbol)
        elif status == "SECONDARY":
            secondary.append(symbol)
        elif status == "WATCH_ONLY":
            watch.append(symbol)
        else:
            reject.append(symbol)

        print(
            f"ACTIVE_FUTURES_ROW family={r['family']} symbol={symbol} "
            f"classification={status} completed={r['completed']} "
            f"success={r['success']} failure={r['failure']} "
            f"expectancy={r['expectancy']} profit_factor={r['profit_factor']} "
            f"winrate={r['winrate']} first_ts={r['first_ts']} last_ts={r['last_ts']}"
        )

    print("\nACTIVE_FUTURES_UNIVERSE_SUMMARY")
    print("primary=" + ",".join(primary))
    print("secondary=" + ",".join(secondary))
    print("watch_only=" + ",".join(watch))
    print("reject=" + ",".join(reject))
    print(f"primary_count={len(primary)}")
    print(f"secondary_count={len(secondary)}")
    print(f"watch_count={len(watch)}")
    print(f"reject_count={len(reject)}")

    if primary:
        print("VERDICT=RS_BOTTOM_ACTIVE_FUTURES_UNIVERSE_READY")
    else:
        print("VERDICT=RS_BOTTOM_ACTIVE_FUTURES_UNIVERSE_EMPTY")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
