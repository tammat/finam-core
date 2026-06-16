#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists trusted_strategy_statistics_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    trades integer not null,
    entry_days integer not null,
    exit_days integer not null,

    pnl numeric not null,
    expectancy numeric not null,
    winrate numeric not null,
    profit_factor numeric not null,

    full_ctx integer not null,
    partial_ctx integer not null,
    weak_ctx integer not null,
    full_ctx_pct numeric not null,

    identity_status text not null,
    trusted_status text not null,
    trusted_reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol, strategy, timeframe, trade_source)
);
"""

DELETE_OLD = """
delete from trusted_strategy_statistics_v1;
"""

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
        coalesce(sum(a.pnl),0) as pnl,
        coalesce(avg(a.pnl),0) as expectancy,
        coalesce(
            count(*) filter (where a.pnl > 0)::numeric / nullif(count(*),0),
            0
        ) as winrate,
        case
            when abs(coalesce(sum(a.pnl) filter (where a.pnl < 0),0)) = 0
                 and coalesce(sum(a.pnl) filter (where a.pnl > 0),0) > 0
                then 999
            when abs(coalesce(sum(a.pnl) filter (where a.pnl < 0),0)) = 0
                then 0
            else
                coalesce(sum(a.pnl) filter (where a.pnl > 0),0)
                / abs(coalesce(sum(a.pnl) filter (where a.pnl < 0),0))
        end as profit_factor,
        count(*) filter (where a.attribution_quality='FULL')::int as full_ctx,
        count(*) filter (where a.attribution_quality='PARTIAL')::int as partial_ctx,
        count(*) filter (where a.attribution_quality='RISK_CONTEXT_WEAK')::int as weak_ctx
    from trade_attribution_v2 a
    join closed_trade_chains_v2 c
      on c.id = a.closed_trade_id
    where coalesce(a.strategy,'') <> ''
      and coalesce(a.timeframe,'') <> ''
    group by a.symbol, a.strategy, a.timeframe, a.trade_source
),
scored as (
    select
        b.*,
        coalesce(g.identity_status, 'NO_IDENTITY_GOVERNANCE') as identity_status,
        coalesce(q.quarantine_status, 'NOT_QUARANTINED') as quarantine_status,
        coalesce(q.quarantine_reason, '') as quarantine_reason,
        coalesce(dq.gate_status, 'BLOCKED') as dq_gate_status,
        coalesce(dq.gate_reason, 'research_data_quality_gate_missing') as dq_gate_reason,
        coalesce(dq.allow_statistics, false) as dq_allow_statistics,
        coalesce(b.full_ctx::numeric / nullif(b.trades,0),0) as full_ctx_pct
    from base b
    left join strategy_identity_governance_v1 g
      on g.symbol = b.symbol
     and g.strategy = b.strategy
     and g.timeframe = b.timeframe
     and g.trade_source = b.trade_source
    left join quarantine_reconstruction_artifacts_v1 q
      on q.symbol = b.symbol
     and q.strategy = b.strategy
     and q.timeframe = b.timeframe
     and q.trade_source = b.trade_source
    left join research_data_quality_gate_v1 dq
      on dq.symbol = b.symbol
     and dq.strategy = b.strategy
     and dq.timeframe = b.timeframe
     and dq.trade_source = b.trade_source
),
verdict as (
    select
        *,
        case
            -- RESEARCH_DATA_QUALITY_GATE_V1_WIRE:
            -- Русский комментарий:
            -- Data Quality Gate имеет самый высокий приоритет.
            -- Если gate закрыт, статистика не может стать trusted.
            when dq_gate_status <> 'OPEN' or dq_allow_statistics = false
                then 'NOT_TRUSTED'
            -- QUARANTINE_RECONSTRUCTION_ARTIFACTS_V1_WIRE:
            -- Русский комментарий:
            -- Карантин имеет приоритет над базовыми правилами trusted scoring.
            when quarantine_status = 'QUARANTINED'
                then 'NOT_TRUSTED'
            when identity_status = 'TIMEFRAME_IDENTITY_SUSPECT'
                then 'NOT_TRUSTED'
            when full_ctx_pct < 0.20
                then 'NOT_TRUSTED'
            when timeframe = 'D1' and (entry_days < 20 or exit_days < 20)
                then 'NOT_TRUSTED'
            when timeframe in ('M5','LIVE') and (entry_days < 10 or exit_days < 10)
                then 'NOT_TRUSTED'
            when timeframe = 'M1' and (entry_days < 10 or exit_days < 10)
                then 'NOT_TRUSTED'
            when timeframe = 'D1' and trades < 50
                then 'NOT_TRUSTED'
            when timeframe = 'M5' and trades < 50
                then 'NOT_TRUSTED'
            when timeframe = 'M1' and trades < 100
                then 'NOT_TRUSTED'
            else 'TRUSTED'
        end as trusted_status,
        case
            -- RESEARCH_DATA_QUALITY_GATE_V1_WIRE:
            -- Русский комментарий:
            -- Причина закрытия DQ gate сохраняется как trusted_reason.
            when dq_gate_status <> 'OPEN' or dq_allow_statistics = false
                then 'dq_gate_block:' || dq_gate_reason
            -- QUARANTINE_RECONSTRUCTION_ARTIFACTS_V1_WIRE:
            -- Русский комментарий:
            -- Причина quarantine сохраняется отдельно в trusted_reason.
            when quarantine_status = 'QUARANTINED'
                then 'quarantined_reconstruction_artifact'
            when identity_status = 'TIMEFRAME_IDENTITY_SUSPECT'
                then 'identity_suspect'
            when full_ctx_pct < 0.20
                then 'low_full_context_pct'
            when timeframe = 'D1' and (entry_days < 20 or exit_days < 20)
                then 'low_time_diversity_d1'
            when timeframe in ('M5','LIVE') and (entry_days < 10 or exit_days < 10)
                then 'low_time_diversity_intraday'
            when timeframe = 'M1' and (entry_days < 10 or exit_days < 10)
                then 'low_time_diversity_m1'
            when timeframe = 'D1' and trades < 50
                then 'low_sample_d1'
            when timeframe = 'M5' and trades < 50
                then 'low_sample_m5'
            when timeframe = 'M1' and trades < 100
                then 'low_sample_m1'
            else 'trusted_statistics_passed'
        end as trusted_reason
    from scored
)
insert into trusted_strategy_statistics_v1 (
    symbol, strategy, timeframe, trade_source,
    trades, entry_days, exit_days,
    pnl, expectancy, winrate, profit_factor,
    full_ctx, partial_ctx, weak_ctx, full_ctx_pct,
    identity_status, trusted_status, trusted_reason,
    runtime_allowed, execution_enabled
)
select
    symbol, strategy, timeframe, trade_source,
    trades, entry_days, exit_days,
    pnl, expectancy, winrate, profit_factor,
    full_ctx, partial_ctx, weak_ctx, full_ctx_pct,
    identity_status, trusted_status, trusted_reason,
    false,
    false
from verdict
on conflict(symbol, strategy, timeframe, trade_source)
do update set
    created_at = now(),
    trades = excluded.trades,
    entry_days = excluded.entry_days,
    exit_days = excluded.exit_days,
    pnl = excluded.pnl,
    expectancy = excluded.expectancy,
    winrate = excluded.winrate,
    profit_factor = excluded.profit_factor,
    full_ctx = excluded.full_ctx,
    partial_ctx = excluded.partial_ctx,
    weak_ctx = excluded.weak_ctx,
    full_ctx_pct = excluded.full_ctx_pct,
    identity_status = excluded.identity_status,
    trusted_status = excluded.trusted_status,
    trusted_reason = excluded.trusted_reason,
    runtime_allowed = false,
    execution_enabled = false;
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
    identity_status,
    trusted_status,
    trusted_reason,
    round(expectancy,6) as expectancy,
    round(profit_factor,4) as profit_factor
from trusted_strategy_statistics_v1
order by
    case when trusted_status='TRUSTED' then 0 else 1 end,
    trades desc,
    symbol,
    strategy,
    timeframe;
"""

SUMMARY = """
select
    count(*) as total,
    count(*) filter (where trusted_status='TRUSTED') as trusted,
    count(*) filter (where trusted_status='NOT_TRUSTED') as not_trusted
from trusted_strategy_statistics_v1;
"""

def main() -> int:
    print("=== TRUSTED STRATEGY STATISTICS V1 ===")
    print("mode=fail_closed")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(DELETE_OLD)
            cur.execute(INSERT)
            cur.execute(SUMMARY)
            summary = cur.fetchone()
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in rows:
        print(
            "TRUSTED_STATS_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"trades={r['trades']} "
            f"entry_days={r['entry_days']} "
            f"exit_days={r['exit_days']} "
            f"full_ctx_pct={r['full_ctx_pct']} "
            f"identity_status={r['identity_status']} "
            f"trusted_status={r['trusted_status']} "
            f"trusted_reason={r['trusted_reason']} "
            f"expectancy={r['expectancy']} "
            f"profit_factor={r['profit_factor']} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "TRUSTED_STRATEGY_STATISTICS_SUMMARY "
        f"total={summary['total']} "
        f"trusted={summary['trusted']} "
        f"not_trusted={summary['not_trusted']} "
        "runtime_allow=0 execution_enabled=0"
    )
    print("TRUSTED_STRATEGY_STATISTICS_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
