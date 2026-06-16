#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DDL = """
create table if not exists strategy_identity_governance_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),
    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null default 'paper',
    identity_status text not null,
    runtime_action text not null,
    allow_paper_signal boolean not null default false,
    allow_radar_signal boolean not null default false,
    allow_real_suggestion boolean not null default false,
    reason text not null,
    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,
    unique(symbol,strategy,timeframe,trade_source)
);
"""

UPSERT = """
insert into strategy_identity_governance_v1 (
    symbol,strategy,timeframe,trade_source,
    identity_status,runtime_action,
    allow_paper_signal,allow_radar_signal,allow_real_suggestion,
    reason,runtime_allowed,execution_enabled
)
select
    a.symbol,
    a.strategy,
    a.timeframe,
    a.trade_source,
    case
        when count(*) >= 100
         and (
              count(distinct c.entry_ts::date) < 10
           or count(distinct c.exit_ts::date) < 10
         )
        then 'TIMEFRAME_IDENTITY_SUSPECT'
        when count(*) = 0
        then 'NO_DATA'
        else 'IDENTITY_RESEARCH_ONLY'
    end as identity_status,
    'BLOCK' as runtime_action,
    false,
    false,
    false,
    case
        when count(*) >= 100
         and (
              count(distinct c.entry_ts::date) < 10
           or count(distinct c.exit_ts::date) < 10
         )
        then 'strategy_identity_suspect:низкая_временная_диверсификация'
        when count(*) = 0
        then 'strategy_identity_no_data'
        else 'strategy_identity_not_enough_evidence_for_runtime'
    end as reason,
    false,
    false
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id = a.closed_trade_id
where coalesce(a.strategy,'') <> ''
  and coalesce(a.timeframe,'') <> ''
group by a.symbol,a.strategy,a.timeframe,a.trade_source
on conflict(symbol,strategy,timeframe,trade_source)
do update set
    identity_status = excluded.identity_status,
    runtime_action = excluded.runtime_action,
    allow_paper_signal = excluded.allow_paper_signal,
    allow_radar_signal = excluded.allow_radar_signal,
    allow_real_suggestion = excluded.allow_real_suggestion,
    reason = excluded.reason,
    runtime_allowed = false,
    execution_enabled = false,
    created_at = now();
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    identity_status,
    runtime_action,
    allow_paper_signal,
    allow_radar_signal,
    allow_real_suggestion,
    reason
from strategy_identity_governance_v1
where identity_status='TIMEFRAME_IDENTITY_SUSPECT'
order by symbol,strategy,timeframe;
"""

def main() -> int:
    print("=== STRATEGY IDENTITY GOVERNANCE V1 ===")
    print("mode=fail_closed")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute(UPSERT)
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in rows:
        print(
            "IDENTITY_GOVERNANCE_BLOCK "
            f"symbol={r[0]} strategy={r[1]} timeframe={r[2]} "
            f"identity_status={r[3]} runtime_action={r[4]} "
            f"paper={r[5]} radar={r[6]} real_suggestion={r[7]} "
            f"reason={r[8]}"
        )

    print(f"STRATEGY_IDENTITY_GOVERNANCE_SUMMARY blocked={len(rows)}")
    print("STRATEGY_IDENTITY_GOVERNANCE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
