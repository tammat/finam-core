#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists research_data_quality_gate_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    trades integer not null,
    entry_days integer not null,
    exit_days integer not null,
    full_ctx_pct numeric not null,

    quarantine_status text not null,
    gate_status text not null,
    gate_reason text not null,

    allow_statistics boolean not null default false,
    allow_walkforward boolean not null default false,
    allow_promotion boolean not null default false,
    allow_runtime boolean not null default false,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol, strategy, timeframe, trade_source)
);
"""

TRUNCATE = "truncate table research_data_quality_gate_v1;"

INSERT = """
with base as (
    select
        a.symbol,
        a.strategy,
        a.timeframe,
        a.trade_source,
        count(*)::int as trades,
        count(distinct c.entry_ts::date)::int as entry_days,
        count(distinct c.exit_ts::date)::int as exit_days,
        coalesce(
            count(*) filter (where a.attribution_quality='FULL')::numeric
            / nullif(count(*),0),
            0
        ) as full_ctx_pct
    from trade_attribution_v2 a
    join closed_trade_chains_v2 c
      on c.id=a.closed_trade_id
    where coalesce(a.strategy,'') <> ''
      and coalesce(a.timeframe,'') <> ''
    group by a.symbol,a.strategy,a.timeframe,a.trade_source
),
scored as (
    select
        b.*,
        coalesce(q.quarantine_status, 'NOT_QUARANTINED') as quarantine_status
    from base b
    left join quarantine_reconstruction_artifacts_v1 q
      on q.symbol=b.symbol
     and q.strategy=b.strategy
     and q.timeframe=b.timeframe
     and q.trade_source=b.trade_source
),
verdict as (
    select
        *,
        case
            when quarantine_status='QUARANTINED'
                then 'BLOCKED'
            when full_ctx_pct < 0.20
                then 'BLOCKED'
            when timeframe='D1' and (entry_days < 20 or exit_days < 20)
                then 'BLOCKED'
            when timeframe in ('M1','M5','LIVE') and (entry_days < 10 or exit_days < 10)
                then 'BLOCKED'
            else 'OPEN'
        end as gate_status,
        case
            when quarantine_status='QUARANTINED'
                then 'quarantined_reconstruction_artifact'
            when full_ctx_pct < 0.20
                then 'low_full_context_pct'
            when timeframe='D1' and (entry_days < 20 or exit_days < 20)
                then 'low_time_diversity_d1'
            when timeframe in ('M1','M5','LIVE') and (entry_days < 10 or exit_days < 10)
                then 'low_time_diversity_intraday'
            else 'research_data_quality_passed'
        end as gate_reason
    from scored
)
insert into research_data_quality_gate_v1 (
    symbol, strategy, timeframe, trade_source,
    trades, entry_days, exit_days, full_ctx_pct,
    quarantine_status, gate_status, gate_reason,
    allow_statistics, allow_walkforward, allow_promotion, allow_runtime,
    runtime_allowed, execution_enabled
)
select
    symbol, strategy, timeframe, trade_source,
    trades, entry_days, exit_days, full_ctx_pct,
    quarantine_status, gate_status, gate_reason,
    gate_status='OPEN',
    gate_status='OPEN',
    gate_status='OPEN',
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
    trades,
    entry_days,
    exit_days,
    round(full_ctx_pct,4) as full_ctx_pct,
    quarantine_status,
    gate_status,
    gate_reason,
    allow_statistics,
    allow_walkforward,
    allow_promotion,
    allow_runtime
from research_data_quality_gate_v1
order by gate_status, symbol, strategy, timeframe;
"""

SUMMARY = """
select
    count(*) total,
    count(*) filter (where gate_status='OPEN') open_rows,
    count(*) filter (where gate_status='BLOCKED') blocked_rows
from research_data_quality_gate_v1;
"""

def main() -> int:
    print("=== RESEARCH DATA QUALITY GATE V1 ===")
    print("mode=fail_closed")
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
            "RESEARCH_DQ_GATE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"trades={r['trades']} "
            f"entry_days={r['entry_days']} "
            f"exit_days={r['exit_days']} "
            f"full_ctx_pct={r['full_ctx_pct']} "
            f"quarantine={r['quarantine_status']} "
            f"gate_status={r['gate_status']} "
            f"reason={r['gate_reason']} "
            f"stats={r['allow_statistics']} "
            f"walkforward={r['allow_walkforward']} "
            f"promotion={r['allow_promotion']} "
            f"runtime={r['allow_runtime']}"
        )

    print(
        "RESEARCH_DATA_QUALITY_GATE_SUMMARY "
        f"total={summary['total']} "
        f"open={summary['open_rows']} "
        f"blocked={summary['blocked_rows']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("RESEARCH_DATA_QUALITY_GATE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
