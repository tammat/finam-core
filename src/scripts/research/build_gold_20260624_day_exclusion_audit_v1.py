#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_20260624_DAY_EXCLUSION_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

sql = """
with base as (
    select
        symbol,
        family,
        status,
        return_pct,
        source_ts,
        (source_ts at time zone 'Europe/Moscow')::date as trade_date_msk,
        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
    from analytics_futures_rs_bottom_paper_observation_v1
    where symbol in ('GDU6@RTSX','GLU6@RTSX')
      and status in ('SUCCESS','FAILURE')
      and return_pct is not null
),
filtered as (
    select *
    from base
    where hour_msk < 19
),
full_stats as (
    select
        symbol,
        'FULL_FILTERED' as mode,
        count(*)::int as completed,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0)) / abs(sum(least(return_pct,0)))
            else null
        end as profit_factor
    from filtered
    group by symbol
),
excluded_day_stats as (
    select
        symbol,
        'EXCLUDE_2026_06_24' as mode,
        count(*)::int as completed,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0)) / abs(sum(least(return_pct,0)))
            else null
        end as profit_factor
    from filtered
    where trade_date_msk <> date '2026-06-24'
    group by symbol
)
select *
from full_stats
union all
select *
from excluded_day_stats
order by symbol, mode;
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

print("\nAUDIT_ROWS")

for r in rows:
    print(
        "AUDIT_ROW "
        f"symbol={r['symbol']} "
        f"mode={r['mode']} "
        f"completed={int(r['completed'] or 0)} "
        f"expectancy={float(r['expectancy'] or 0):.4f} "
        f"net_return={float(r['net_return'] or 0):.4f} "
        f"profit_factor={float(r['profit_factor'] or 0):.4f}"
    )

print("\nINTERPRETATION")
print("if PF restored after exclusion -> ONE_DAY_ANOMALY")
print("if PF remains broken -> STRUCTURAL_FAILURE")

print("\nVERDICT=GOLD_20260624_DAY_EXCLUSION_AUDIT_READY")
