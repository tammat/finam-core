#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

SYMBOLS = ("GDU6@RTSX", "GLU6@RTSX")


def fmt(v):
    if v is None:
        return "NONE"
    return f"{float(v):.4f}"


dsn = os.environ["DATABASE_URL"]

sql = """
with base as (
    select
        symbol,
        return_pct,
        extract(hour from signal_ts at time zone 'Europe/Moscow')::int as hour_msk
    from analytics_rs_bottom_runtime_dry_run_v1
    where symbol = any(%s)
      and status in ('SUCCESS','FAILURE')
      and return_pct is not null
),
full_stats as (
    select
        symbol,
        count(*)::int as completed,
        avg(return_pct) as avg_return,
        sum(return_pct) as total_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0))
               / abs(sum(least(return_pct,0)))
            else null
        end as pf
    from base
    group by symbol
),
filtered_stats as (
    select
        symbol,
        count(*)::int as completed,
        avg(return_pct) as avg_return,
        sum(return_pct) as total_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0))
               / abs(sum(least(return_pct,0)))
            else null
        end as pf
    from base
    where hour_msk < 19
    group by symbol
)
select
    f.symbol,

    f.completed as full_completed,
    f.avg_return as full_avg_return,
    f.total_return as full_total_return,
    f.pf as full_pf,

    x.completed as filtered_completed,
    x.avg_return as filtered_avg_return,
    x.total_return as filtered_total_return,
    x.pf as filtered_pf

from full_stats f
left join filtered_stats x using(symbol)
order by symbol
"""

print("=== EVENING_SESSION_FILTER_PLAN_V1 ===")
print("mode=dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql, (list(SYMBOLS),))
        rows = cur.fetchall()

for r in rows:
    print(
        "FILTER_ROW "
        f"symbol={r['symbol']} "
        f"full_completed={r['full_completed']} "
        f"full_pf={fmt(r['full_pf'])} "
        f"full_avg_return={fmt(r['full_avg_return'])} "
        f"full_total_return={fmt(r['full_total_return'])} "
        f"filtered_completed={r['filtered_completed']} "
        f"filtered_pf={fmt(r['filtered_pf'])} "
        f"filtered_avg_return={fmt(r['filtered_avg_return'])} "
        f"filtered_total_return={fmt(r['filtered_total_return'])}"
    )

print("VERDICT=EVENING_SESSION_FILTER_PLAN_READY")
