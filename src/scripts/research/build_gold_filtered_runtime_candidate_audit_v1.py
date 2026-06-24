#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_FILTERED_RUNTIME_CANDIDATE_AUDIT_V1 ===")
print("mode=read_only_audit")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
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
agg as (
    select
        symbol,
        coalesce(max(family), 'GOLD') as family,
        count(*)::int as completed,
        count(*) filter (where return_pct > 0)::int as wins,
        count(*) filter (where return_pct <= 0)::int as losses,
        avg(return_pct) as expectancy,
        sum(return_pct) as net_return,
        count(*) * 0.02 as estimated_fee_drag,
        sum(return_pct) - count(*) * 0.02 as net_after_fee_estimate,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0)) / abs(sum(least(return_pct,0)))
            else null
        end as profit_factor,
        min(source_ts) as first_ts,
        max(source_ts) as last_ts
    from filtered
    group by symbol
),
recent as (
    select
        symbol,
        count(*)::int as recent_completed,
        avg(return_pct) as recent_expectancy,
        sum(return_pct) as recent_net_return,
        case
            when abs(sum(least(return_pct,0))) > 0
            then sum(greatest(return_pct,0)) / abs(sum(least(return_pct,0)))
            else null
        end as recent_pf
    from filtered
    where source_ts >= now() - interval '24 hour'
    group by symbol
),
daily as (
    select
        symbol,
        trade_date_msk,
        count(*)::int as daily_completed,
        sum(return_pct) as daily_net_return
    from filtered
    group by symbol, trade_date_msk
),
daily_concentration as (
    select
        symbol,
        max(daily_net_return) as best_day_return,
        min(daily_net_return) as worst_day_return,
        max(daily_completed) as max_day_completed,
        count(*)::int as days_count
    from daily
    group by symbol
)
select
    a.symbol,
    a.family,
    a.completed,
    a.wins,
    a.losses,
    a.expectancy,
    a.net_return,
    a.estimated_fee_drag,
    a.net_after_fee_estimate,
    a.profit_factor,
    a.first_ts,
    a.last_ts,
    coalesce(r.recent_completed, 0) as recent_completed,
    r.recent_expectancy,
    r.recent_net_return,
    r.recent_pf,
    d.best_day_return,
    d.worst_day_return,
    d.max_day_completed,
    d.days_count
from agg a
left join recent r using (symbol)
left join daily_concentration d using (symbol)
order by a.profit_factor desc nulls last, a.completed desc;
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

print("\nAUDIT_ROWS")

ready = 0
research_only = 0

for r in rows:
    completed = int(r["completed"] or 0)
    pf = float(r["profit_factor"] or 0)
    exp = float(r["expectancy"] or 0)
    net_return = float(r["net_return"] or 0)
    net_after_fee = float(r["net_after_fee_estimate"] or 0)

    recent_completed = int(r["recent_completed"] or 0)
    recent_pf = float(r["recent_pf"] or 0)
    recent_exp = float(r["recent_expectancy"] or 0)
    recent_net = float(r["recent_net_return"] or 0)

    best_day = float(r["best_day_return"] or 0)
    days_count = int(r["days_count"] or 0)

    fee_drag_ok = net_after_fee > 0
    recent_ok = recent_completed == 0 or (recent_pf >= 1.0 and recent_exp >= 0 and recent_net >= 0)
    concentration_ok = days_count >= 2 and (best_day / net_return <= 0.80 if net_return > 0 else False)

    core_ok = completed >= 50 and pf >= 1.5 and exp > 0 and net_return > 0

    if core_ok and fee_drag_ok and recent_ok and concentration_ok:
        verdict = "READY_FOR_RUNTIME_CANDIDATE"
        ready += 1
    else:
        verdict = "KEEP_RESEARCH_ONLY"
        research_only += 1

    print(
        "AUDIT_ROW "
        f"symbol={r['symbol']} "
        f"family={r['family']} "
        f"completed={completed} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"profit_factor={pf:.4f} "
        f"expectancy={exp:.4f} "
        f"net_return={net_return:.4f} "
        f"estimated_fee_drag={float(r['estimated_fee_drag'] or 0):.4f} "
        f"net_after_fee_estimate={net_after_fee:.4f} "
        f"recent_completed={recent_completed} "
        f"recent_pf={recent_pf:.4f} "
        f"recent_expectancy={recent_exp:.4f} "
        f"recent_net_return={recent_net:.4f} "
        f"days_count={days_count} "
        f"best_day_return={best_day:.4f} "
        f"worst_day_return={float(r['worst_day_return'] or 0):.4f} "
        f"max_day_completed={int(r['max_day_completed'] or 0)} "
        f"core_ok={1 if core_ok else 0} "
        f"fee_drag_ok={1 if fee_drag_ok else 0} "
        f"recent_ok={1 if recent_ok else 0} "
        f"concentration_ok={1 if concentration_ok else 0} "
        f"verdict={verdict}"
    )

print("\nAUDIT_SUMMARY")
print(f"ready_for_runtime_candidate={ready}")
print(f"keep_research_only={research_only}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

if ready > 0:
    print("VERDICT=GOLD_FILTERED_RUNTIME_CANDIDATE_AUDIT_READY")
else:
    print("VERDICT=GOLD_FILTERED_RUNTIME_CANDIDATE_AUDIT_RESEARCH_ONLY")
