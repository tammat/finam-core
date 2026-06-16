#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists strategy_statistics_v3 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,
    quality_bucket text not null,

    trades integer not null,
    entry_days integer not null,
    exit_days integer not null,

    net_pnl numeric not null,
    expectancy numeric not null,
    winrate numeric not null,
    profit_factor numeric not null,

    full_rows integer not null,
    partial_rows integer not null,

    statistics_status text not null,
    statistics_reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol, strategy, timeframe, trade_source, quality_bucket)
);
"""

TRUNCATE = "truncate table strategy_statistics_v3;"

INSERT = """
with base as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        case
            when attribution_quality='FULL' then 'FULL_ONLY'
            when attribution_quality='PARTIAL' then 'PARTIAL_ONLY'
            else 'OTHER'
        end as quality_bucket,
        count(*)::int as trades,
        count(distinct entry_ts::date)::int as entry_days,
        count(distinct exit_ts::date)::int as exit_days,
        coalesce(sum(net_pnl),0) as net_pnl,
        coalesce(avg(net_pnl),0) as expectancy,
        coalesce(
            count(*) filter (where net_pnl > 0)::numeric / nullif(count(*),0),
            0
        ) as winrate,
        case
            when abs(coalesce(sum(net_pnl) filter (where net_pnl < 0),0)) = 0
                 and coalesce(sum(net_pnl) filter (where net_pnl > 0),0) > 0
                then 999
            when abs(coalesce(sum(net_pnl) filter (where net_pnl < 0),0)) = 0
                then 0
            else
                coalesce(sum(net_pnl) filter (where net_pnl > 0),0)
                / abs(coalesce(sum(net_pnl) filter (where net_pnl < 0),0))
        end as profit_factor,
        count(*) filter (where attribution_quality='FULL')::int as full_rows,
        count(*) filter (where attribution_quality='PARTIAL')::int as partial_rows
    from trade_attribution_v3
    where attribution_quality in ('FULL','PARTIAL')
    group by
        symbol,
        strategy,
        timeframe,
        trade_source,
        case
            when attribution_quality='FULL' then 'FULL_ONLY'
            when attribution_quality='PARTIAL' then 'PARTIAL_ONLY'
            else 'OTHER'
        end
),
verdict as (
    select
        *,
        case
            when quality_bucket <> 'FULL_ONLY'
                then 'RESEARCH_ONLY'
            when trades < 50
                then 'LOW_SAMPLE'
            when timeframe='M5' and (entry_days < 10 or exit_days < 10)
                then 'LOW_TIME_DIVERSITY'
            when timeframe='M1' and (entry_days < 10 or exit_days < 10)
                then 'LOW_TIME_DIVERSITY'
            when timeframe='D1' and (entry_days < 20 or exit_days < 20)
                then 'LOW_TIME_DIVERSITY'
            else 'STATISTICALLY_REVIEWABLE'
        end as statistics_status,
        case
            when quality_bucket <> 'FULL_ONLY'
                then 'partial_quality_research_only'
            when trades < 50
                then 'low_sample'
            when timeframe in ('M1','M5') and (entry_days < 10 or exit_days < 10)
                then 'low_time_diversity_intraday'
            when timeframe='D1' and (entry_days < 20 or exit_days < 20)
                then 'low_time_diversity_d1'
            else 'statistics_v3_reviewable'
        end as statistics_reason
    from base
)
insert into strategy_statistics_v3 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    quality_bucket,
    trades,
    entry_days,
    exit_days,
    net_pnl,
    expectancy,
    winrate,
    profit_factor,
    full_rows,
    partial_rows,
    statistics_status,
    statistics_reason,
    runtime_allowed,
    execution_enabled
)
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    quality_bucket,
    trades,
    entry_days,
    exit_days,
    net_pnl,
    expectancy,
    winrate,
    profit_factor,
    full_rows,
    partial_rows,
    statistics_status,
    statistics_reason,
    false,
    false
from verdict
on conflict(symbol, strategy, timeframe, trade_source, quality_bucket)
do update set
    created_at = now(),
    trades = excluded.trades,
    entry_days = excluded.entry_days,
    exit_days = excluded.exit_days,
    net_pnl = excluded.net_pnl,
    expectancy = excluded.expectancy,
    winrate = excluded.winrate,
    profit_factor = excluded.profit_factor,
    full_rows = excluded.full_rows,
    partial_rows = excluded.partial_rows,
    statistics_status = excluded.statistics_status,
    statistics_reason = excluded.statistics_reason,
    runtime_allowed = false,
    execution_enabled = false;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    quality_bucket,
    trades,
    entry_days,
    exit_days,
    round(net_pnl,6) as net_pnl,
    round(expectancy,6) as expectancy,
    round(winrate,4) as winrate,
    round(profit_factor,4) as profit_factor,
    full_rows,
    partial_rows,
    statistics_status,
    statistics_reason
from strategy_statistics_v3
order by symbol,strategy,timeframe,quality_bucket;
"""

SUMMARY = """
select
    count(*) total,
    count(*) filter (where statistics_status='STATISTICALLY_REVIEWABLE') reviewable,
    count(*) filter (where statistics_status='LOW_SAMPLE') low_sample,
    count(*) filter (where statistics_status='LOW_TIME_DIVERSITY') low_time_diversity,
    count(*) filter (where statistics_status='RESEARCH_ONLY') research_only
from strategy_statistics_v3;
"""

def main() -> int:
    print("=== STRATEGY STATISTICS V3 FROM ATTRIBUTION V3 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(INSERT)
            cur.execute(SUMMARY)
            summary = cur.fetchone()
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in rows:
        print(
            "STRATEGY_STATS_V3_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"bucket={r['quality_bucket']} "
            f"trades={r['trades']} "
            f"entry_days={r['entry_days']} "
            f"exit_days={r['exit_days']} "
            f"net_pnl={r['net_pnl']} "
            f"expectancy={r['expectancy']} "
            f"winrate={r['winrate']} "
            f"profit_factor={r['profit_factor']} "
            f"full={r['full_rows']} "
            f"partial={r['partial_rows']} "
            f"status={r['statistics_status']} "
            f"reason={r['statistics_reason']} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "STRATEGY_STATISTICS_V3_SUMMARY "
        f"total={summary['total']} "
        f"reviewable={summary['reviewable']} "
        f"low_sample={summary['low_sample']} "
        f"low_time_diversity={summary['low_time_diversity']} "
        f"research_only={summary['research_only']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("STRATEGY_STATISTICS_V3_FROM_ATTRIBUTION_V3_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
