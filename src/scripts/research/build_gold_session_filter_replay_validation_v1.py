#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_SESSION_FILTER_REPLAY_VALIDATION_V1 ===")
print("mode=replay_validation")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=analytics_futures_rs_bottom_paper_observation_v1")
print("timestamp_column=source_ts")

sql = """
with base as (
    select
        symbol,
        source_ts,
        return_pct,
        status,
        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
    from analytics_futures_rs_bottom_paper_observation_v1
    where symbol in ('GDU6@RTSX','GLU6@RTSX')
      and status in ('SUCCESS','FAILURE')
      and return_pct is not null
),
windows as (
    select 7 as lookback_days
    union all select 14
    union all select 30
),
expanded as (
    select
        w.lookback_days,
        b.*
    from windows w
    join base b
      on b.source_ts >= now() - make_interval(days => w.lookback_days)
),
agg as (
    select
        lookback_days,
        symbol,
        'FULL_SESSION' as mode,
        count(*)::int as completed,
        count(*) filter (where return_pct > 0)::int as wins,
        count(*) filter (where return_pct <= 0)::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0))
                 / abs(sum(least(return_pct,0)))
            else null
        end as profit_factor
    from expanded
    group by lookback_days, symbol

    union all

    select
        lookback_days,
        symbol,
        'FILTER_BEFORE_19_MSK' as mode,
        count(*)::int,
        count(*) filter (where return_pct > 0)::int,
        count(*) filter (where return_pct <= 0)::int,
        avg(return_pct),
        sum(return_pct),
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0))
                 / abs(sum(least(return_pct,0)))
            else null
        end
    from expanded
    where hour_msk < 19
    group by lookback_days, symbol
)
select *
from agg
order by lookback_days, symbol, mode;
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

print("\nVALIDATION_ROWS")

for r in rows:
    print(
        "VALIDATION_ROW "
        f"lookback_days={r['lookback_days']} "
        f"symbol={r['symbol']} "
        f"mode={r['mode']} "
        f"completed={r['completed']} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"expectancy={float(r['expectancy'] or 0):.4f} "
        f"net_return={float(r['net_return'] or 0):.4f} "
        f"profit_factor={float(r['profit_factor'] or 0):.4f}"
    )

print("\nVERDICT=GOLD_SESSION_FILTER_REPLAY_VALIDATION_READY")
