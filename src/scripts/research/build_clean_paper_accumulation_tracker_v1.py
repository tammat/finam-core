#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists clean_paper_accumulation_tracker_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    clean_trades bigint not null,
    clean_fills bigint not null,
    first_trade_ts timestamptz,
    last_trade_ts timestamptz,
    trade_days bigint not null,

    v3_chains bigint not null default 0,
    v3_full_chains bigint not null default 0,
    v3_partial_chains bigint not null default 0,
    v3_net_pnl numeric not null default 0,

    accumulation_status text not null,
    accumulation_reason text not null,

    research_allowed boolean not null default false,
    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol, strategy, timeframe, trade_source)
);
"""

TRUNCATE = "truncate table clean_paper_accumulation_tracker_v1;"

INSERT = """
with clean_trades as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        count(*)::bigint as clean_trades,
        count(*)::bigint as clean_fills,
        min(created_at) as first_trade_ts,
        max(created_at) as last_trade_ts,
        count(distinct created_at::date)::bigint as trade_days
    from trades
    where origin='paper'
      and trade_source='paper'
      and coalesce(strategy,'') <> ''
      and coalesce(timeframe,'') <> ''
      and coalesce(is_invalid,false)=false
    group by symbol,strategy,timeframe,trade_source
),
chains as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        count(*)::bigint as v3_chains,
        count(*) filter (where quality_status='FULL')::bigint as v3_full_chains,
        count(*) filter (where quality_status='PARTIAL')::bigint as v3_partial_chains,
        coalesce(sum(net_pnl),0)::numeric as v3_net_pnl
    from closed_trade_chains_v3
    group by symbol,strategy,timeframe,trade_source
),
joined as (
    select
        t.symbol,
        t.strategy,
        t.timeframe,
        t.trade_source,
        t.clean_trades,
        t.clean_fills,
        t.first_trade_ts,
        t.last_trade_ts,
        t.trade_days,
        coalesce(c.v3_chains,0) as v3_chains,
        coalesce(c.v3_full_chains,0) as v3_full_chains,
        coalesce(c.v3_partial_chains,0) as v3_partial_chains,
        coalesce(c.v3_net_pnl,0) as v3_net_pnl
    from clean_trades t
    left join chains c
      on c.symbol=t.symbol
     and c.strategy=t.strategy
     and c.timeframe=t.timeframe
     and c.trade_source=t.trade_source
),
verdict as (
    select
        *,
        case
            when v3_full_chains >= 100 and trade_days >= 20 then 'RESEARCH_READY'
            when v3_full_chains >= 30 and trade_days >= 10 then 'ACCUMULATING'
            when v3_full_chains > 0 then 'EARLY_ACCUMULATION'
            else 'NO_V3_CHAINS'
        end as accumulation_status,
        case
            when v3_full_chains >= 100 and trade_days >= 20 then 'enough_clean_full_chains_for_research_review'
            when v3_full_chains >= 30 and trade_days >= 10 then 'clean_data_accumulating_not_enough_for_review'
            when v3_full_chains > 0 then 'too_few_clean_full_chains'
            else 'clean_trades_exist_but_no_v3_chains'
        end as accumulation_reason
    from joined
)
insert into clean_paper_accumulation_tracker_v1 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    clean_trades,
    clean_fills,
    first_trade_ts,
    last_trade_ts,
    trade_days,
    v3_chains,
    v3_full_chains,
    v3_partial_chains,
    v3_net_pnl,
    accumulation_status,
    accumulation_reason,
    research_allowed,
    runtime_allowed,
    execution_enabled
)
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    clean_trades,
    clean_fills,
    first_trade_ts,
    last_trade_ts,
    trade_days,
    v3_chains,
    v3_full_chains,
    v3_partial_chains,
    v3_net_pnl,
    accumulation_status,
    accumulation_reason,
    accumulation_status='RESEARCH_READY',
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
    clean_trades,
    trade_days,
    v3_chains,
    v3_full_chains,
    v3_partial_chains,
    round(v3_net_pnl,6) as v3_net_pnl,
    accumulation_status,
    accumulation_reason,
    research_allowed,
    runtime_allowed,
    execution_enabled
from clean_paper_accumulation_tracker_v1
order by
    case accumulation_status
        when 'RESEARCH_READY' then 0
        when 'ACCUMULATING' then 1
        when 'EARLY_ACCUMULATION' then 2
        else 3
    end,
    v3_full_chains desc,
    clean_trades desc;
"""

SUMMARY = """
select
    accumulation_status,
    count(*) rows,
    sum(clean_trades) clean_trades,
    sum(v3_full_chains) v3_full_chains
from clean_paper_accumulation_tracker_v1
group by accumulation_status
order by accumulation_status;
"""

def main() -> int:
    print("=== CLEAN PAPER ACCUMULATION TRACKER V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(INSERT)
            cur.execute(SUMMARY)
            summary = cur.fetchall()
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in summary:
        print(
            "CLEAN_PAPER_ACCUMULATION_SUMMARY "
            f"status={r['accumulation_status']} "
            f"rows={r['rows']} "
            f"clean_trades={r['clean_trades']} "
            f"v3_full_chains={r['v3_full_chains']}"
        )

    for r in rows:
        print(
            "CLEAN_PAPER_ACCUMULATION_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"clean_trades={r['clean_trades']} "
            f"trade_days={r['trade_days']} "
            f"v3_chains={r['v3_chains']} "
            f"v3_full_chains={r['v3_full_chains']} "
            f"v3_partial_chains={r['v3_partial_chains']} "
            f"v3_net_pnl={r['v3_net_pnl']} "
            f"status={r['accumulation_status']} "
            f"reason={r['accumulation_reason']} "
            f"research={r['research_allowed']} "
            f"runtime={r['runtime_allowed']} "
            f"execution={r['execution_enabled']}"
        )

    print("CLEAN_PAPER_ACCUMULATION_TRACKER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
