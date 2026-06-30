#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_RECENT_DEGRADATION_ROOT_CAUSE_AUDIT_V1 ===")
print("mode=read_only_root_cause")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("symbols=GDU6@RTSX,GLU6@RTSX")
print("edge_mode=FILTERED_BEFORE_19_MSK")

sql = """
with base as (
    select
        symbol,
        family,
        status,
        return_pct,
        source_ts,
        created_at,
        (source_ts at time zone 'Europe/Moscow')::date as trade_date_msk,
        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk,
        'UNAVAILABLE_NO_PAYLOAD_COLUMN'::text as side,
        'UNAVAILABLE_NO_PAYLOAD_COLUMN'::text as signal_class
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
cut as (
    select max(source_ts) - interval '24 hour' as recent_from
    from filtered
),
bucketed as (
    select
        f.*,
        case when f.source_ts >= c.recent_from then 'RECENT_24H' else 'PRIOR' end as period
    from filtered f
    cross join cut c
),
agg as (
    select
        symbol,
        period,
        count(*)::int as completed,
        count(*) filter (where return_pct > 0)::int as wins,
        count(*) filter (where return_pct <= 0)::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0)) / abs(sum(least(return_pct,0)))
            else null
        end as profit_factor
    from bucketed
    group by symbol, period
),
by_day as (
    select
        symbol,
        trade_date_msk::text as bucket,
        count(*)::int as completed,
        null::int as wins,
        null::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        null::numeric as profit_factor
    from filtered
    group by symbol, trade_date_msk
),
by_hour as (
    select
        symbol,
        hour_msk::text as bucket,
        count(*)::int as completed,
        null::int as wins,
        null::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        null::numeric as profit_factor
    from filtered
    group by symbol, hour_msk
),
by_side as (
    select
        symbol,
        side as bucket,
        count(*)::int as completed,
        null::int as wins,
        null::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        null::numeric as profit_factor
    from filtered
    group by symbol, side
),
by_signal_class as (
    select
        symbol,
        signal_class as bucket,
        count(*)::int as completed,
        null::int as wins,
        null::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        null::numeric as profit_factor
    from filtered
    group by symbol, signal_class
)
select 'PERIOD' as section, symbol, period as bucket, completed, wins, losses, expectancy, net_return, profit_factor
from agg
union all
select 'DAY', symbol, bucket, completed, wins, losses, expectancy, net_return, profit_factor
from by_day
union all
select 'HOUR', symbol, bucket, completed, wins, losses, expectancy, net_return, profit_factor
from by_hour
union all
select 'SIDE', symbol, bucket, completed, wins, losses, expectancy, net_return, profit_factor
from by_side
union all
select 'SIGNAL_CLASS', symbol, bucket, completed, wins, losses, expectancy, net_return, profit_factor
from by_signal_class
order by section, symbol, net_return nulls last;
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

print("\nROOT_CAUSE_ROWS")

for r in rows:
    print(
        "ROOT_CAUSE_ROW "
        f"section={r['section']} "
        f"symbol={r['symbol']} "
        f"bucket={str(r['bucket']).replace(' ', '_')} "
        f"completed={r['completed']} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"expectancy={float(r['expectancy'] or 0):.4f} "
        f"net_return={float(r['net_return'] or 0):.4f} "
        f"profit_factor={float(r['profit_factor'] or 0):.4f}"
    )

print("\nROOT_CAUSE_HINTS")
print("check=PERIOD shows recent degradation vs prior")
print("check=DAY shows one-day anomaly or multi-day decay")
print("check=HOUR shows intraday/session drift")
print("check=SIDE shows direction drift if side is available")
print("check=SIGNAL_CLASS shows setup drift if payload has signal class")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=GOLD_RECENT_DEGRADATION_ROOT_CAUSE_AUDIT_READY")
