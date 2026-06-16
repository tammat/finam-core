#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

MAX_CHAINS_PER_MINUTE = 10
MAX_FILLS_PER_MINUTE = 20

DDL = """
create table if not exists v3_burst_artifact_gate (
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

    max_chains_per_minute integer not null,
    max_fills_per_minute integer not null,

    burst_status text not null,
    burst_reason text not null,

    allow_statistics boolean not null default false,
    allow_walkforward boolean not null default false,
    allow_promotion boolean not null default false,
    allow_runtime boolean not null default false,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol, strategy, timeframe, trade_source, quality_bucket)
);
"""

TRUNCATE = "truncate table v3_burst_artifact_gate;"

INSERT = """
with stats as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        quality_bucket,
        trades,
        entry_days,
        exit_days
    from strategy_statistics_v3
),
chains_per_minute as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        case
            when quality_status='FULL' then 'FULL_ONLY'
            when quality_status='PARTIAL' then 'PARTIAL_ONLY'
            else 'OTHER'
        end as quality_bucket,
        date_trunc('minute', entry_ts) as minute_bucket,
        count(*)::int as chains
    from closed_trade_chains_v3
    group by
        symbol,
        strategy,
        timeframe,
        trade_source,
        case
            when quality_status='FULL' then 'FULL_ONLY'
            when quality_status='PARTIAL' then 'PARTIAL_ONLY'
            else 'OTHER'
        end,
        date_trunc('minute', entry_ts)
),
max_chains as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        quality_bucket,
        max(chains)::int as max_chains_per_minute
    from chains_per_minute
    group by symbol,strategy,timeframe,trade_source,quality_bucket
),
fills_per_minute as (
    select
        t.symbol,
        t.strategy,
        t.timeframe,
        t.trade_source,
        date_trunc('minute', t.created_at) as minute_bucket,
        count(*)::int as fills
    from trades t
    where coalesce(t.strategy,'') <> ''
      and coalesce(t.timeframe,'') <> ''
      and coalesce(t.is_invalid,false)=false
    group by
        t.symbol,
        t.strategy,
        t.timeframe,
        t.trade_source,
        date_trunc('minute', t.created_at)
),
max_fills as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        max(fills)::int as max_fills_per_minute
    from fills_per_minute
    group by symbol,strategy,timeframe,trade_source
),
scored as (
    select
        s.*,
        coalesce(mc.max_chains_per_minute,0) as max_chains_per_minute,
        coalesce(mf.max_fills_per_minute,0) as max_fills_per_minute
    from stats s
    left join max_chains mc
      on mc.symbol=s.symbol
     and mc.strategy=s.strategy
     and mc.timeframe=s.timeframe
     and mc.trade_source=s.trade_source
     and mc.quality_bucket=s.quality_bucket
    left join max_fills mf
      on mf.symbol=s.symbol
     and mf.strategy=s.strategy
     and mf.timeframe=s.timeframe
     and mf.trade_source=s.trade_source
),
verdict as (
    select
        *,
        case
            when max_chains_per_minute > %(max_chains_per_minute)s
                then 'BURST_ARTIFACT'
            when max_fills_per_minute > %(max_fills_per_minute)s
                then 'BURST_ARTIFACT'
            else 'NO_BURST_DETECTED'
        end as burst_status,
        case
            when max_chains_per_minute > %(max_chains_per_minute)s
                then 'max_chains_per_minute_exceeded'
            when max_fills_per_minute > %(max_fills_per_minute)s
                then 'max_fills_per_minute_exceeded'
            else 'burst_gate_passed'
        end as burst_reason
    from scored
)
insert into v3_burst_artifact_gate (
    symbol,
    strategy,
    timeframe,
    trade_source,
    quality_bucket,
    trades,
    entry_days,
    exit_days,
    max_chains_per_minute,
    max_fills_per_minute,
    burst_status,
    burst_reason,
    allow_statistics,
    allow_walkforward,
    allow_promotion,
    allow_runtime,
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
    max_chains_per_minute,
    max_fills_per_minute,
    burst_status,
    burst_reason,
    burst_status='NO_BURST_DETECTED',
    burst_status='NO_BURST_DETECTED',
    false,
    false,
    false,
    false
from verdict;
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
    max_chains_per_minute,
    max_fills_per_minute,
    burst_status,
    burst_reason,
    allow_statistics,
    allow_walkforward,
    allow_promotion,
    allow_runtime
from v3_burst_artifact_gate
order by
    case when burst_status='BURST_ARTIFACT' then 0 else 1 end,
    symbol,
    strategy,
    timeframe,
    quality_bucket;
"""

SUMMARY = """
select
    count(*) total,
    count(*) filter (where burst_status='BURST_ARTIFACT') burst_artifacts,
    count(*) filter (where burst_status='NO_BURST_DETECTED') no_burst
from v3_burst_artifact_gate;
"""

def main() -> int:
    print("=== V3 BURST ARTIFACT GATE ===")
    print("mode=fail_closed")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"max_chains_per_minute_threshold={MAX_CHAINS_PER_MINUTE}")
    print(f"max_fills_per_minute_threshold={MAX_FILLS_PER_MINUTE}")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(
                INSERT,
                {
                    "max_chains_per_minute": MAX_CHAINS_PER_MINUTE,
                    "max_fills_per_minute": MAX_FILLS_PER_MINUTE,
                },
            )
            cur.execute(SUMMARY)
            summary = cur.fetchone()
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in rows:
        print(
            "V3_BURST_GATE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"bucket={r['quality_bucket']} "
            f"trades={r['trades']} "
            f"entry_days={r['entry_days']} "
            f"exit_days={r['exit_days']} "
            f"max_chains_per_minute={r['max_chains_per_minute']} "
            f"max_fills_per_minute={r['max_fills_per_minute']} "
            f"burst_status={r['burst_status']} "
            f"reason={r['burst_reason']} "
            f"stats={r['allow_statistics']} "
            f"walkforward={r['allow_walkforward']} "
            f"promotion={r['allow_promotion']} "
            f"runtime={r['allow_runtime']} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "V3_BURST_ARTIFACT_GATE_SUMMARY "
        f"total={summary['total']} "
        f"burst_artifacts={summary['burst_artifacts']} "
        f"no_burst={summary['no_burst']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("V3_BURST_ARTIFACT_GATE_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
