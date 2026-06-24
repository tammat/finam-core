#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_FILTERED_EDGE_SCORECARD_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("filter=hour_msk<19")

sql = """
with base as (
    select
        symbol,
        family,
        status,
        return_pct,
        source_ts,
        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
    from analytics_futures_rs_bottom_paper_observation_v1
    where symbol in ('GDU6@RTSX','GLU6@RTSX')
      and status in ('SUCCESS','FAILURE')
      and return_pct is not null
),
agg as (
    select
        symbol,
        coalesce(max(family), 'GOLD') as family,
        'FILTERED_BEFORE_19_MSK' as edge_mode,
        count(*)::int as completed,
        count(*) filter (where return_pct > 0)::int as wins,
        count(*) filter (where return_pct <= 0)::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0)) / abs(sum(least(return_pct,0)))
            else null
        end as profit_factor,
        min(source_ts) as first_ts,
        max(source_ts) as last_ts
    from base
    where hour_msk < 19
    group by symbol
)
select *
from agg
order by profit_factor desc nulls last, completed desc;
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

print("\nFILTERED_SCORECARD_ROWS")

for r in rows:
    completed = int(r["completed"] or 0)
    pf = float(r["profit_factor"] or 0)
    exp = float(r["expectancy"] or 0)
    verdict = "PRIMARY" if completed >= 15 and pf >= 1.5 and exp > 0 else "WATCH"

    print(
        "FILTERED_ROW "
        f"symbol={r['symbol']} "
        f"family={r['family']} "
        f"edge_mode={r['edge_mode']} "
        f"completed={completed} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"expectancy={exp:.4f} "
        f"net_return={float(r['net_return'] or 0):.4f} "
        f"profit_factor={pf:.4f} "
        f"verdict={verdict} "
        f"first_ts={r['first_ts']} "
        f"last_ts={r['last_ts']}"
    )

print("\nVERDICT=GOLD_FILTERED_EDGE_SCORECARD_READY")
