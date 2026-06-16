#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists gold_synthetic_exit_policy_audit_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    entry_trade_id bigint not null,
    symbol text not null,
    strategy text not null,
    timeframe text not null,

    entry_ts timestamptz not null,
    entry_side text not null,
    entry_price numeric not null,

    exit_policy text not null,
    exit_bars int not null,
    exit_ts timestamptz,
    exit_price numeric,

    synthetic_exit_side text not null,
    pnl numeric,
    status text not null,
    reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false
);
"""

TRUNCATE = "truncate table gold_synthetic_exit_policy_audit_v1;"

INSERT = """
insert into gold_synthetic_exit_policy_audit_v1 (
    entry_trade_id,
    symbol,
    strategy,
    timeframe,
    entry_ts,
    entry_side,
    entry_price,
    exit_policy,
    exit_bars,
    exit_ts,
    exit_price,
    synthetic_exit_side,
    pnl,
    status,
    reason,
    runtime_allowed,
    execution_enabled
)
with entries as (
    select
        id as entry_trade_id,
        symbol,
        strategy,
        timeframe,
        created_at as entry_ts,
        side as entry_side,
        price as entry_price
    from trades
    where origin = 'paper'
      and trade_source = 'paper'
      and symbol = 'GDU6@RTSX'
      and strategy = 'gold_short_only_shadow_v1'
      and timeframe = 'M5'
      and side = 'SELL'
),
policies(exit_policy, exit_bars) as (
    values
        ('TIME_EXIT_M5_3BARS', 3),
        ('TIME_EXIT_M5_6BARS', 6),
        ('TIME_EXIT_M5_12BARS', 12)
),
matched as (
    select
        e.*,
        p.exit_policy,
        p.exit_bars,
        b.ts as exit_ts,
        b.close as exit_price,
        row_number() over (
            partition by e.entry_trade_id, p.exit_policy
            order by b.ts
        ) as rn
    from entries e
    cross join policies p
    left join market_bars b
      on b.symbol = e.symbol
     and b.timeframe = 'M5'
     and b.ts >= e.entry_ts + (p.exit_bars * interval '5 minutes')
)
select
    entry_trade_id,
    symbol,
    strategy,
    timeframe,
    entry_ts,
    entry_side,
    entry_price,
    exit_policy,
    exit_bars,
    exit_ts,
    exit_price,
    'BUY' as synthetic_exit_side,
    case
        when exit_price is not null then entry_price - exit_price
        else null
    end as pnl,
    case
        when exit_price is not null then 'EXIT_CANDIDATE'
        else 'NO_EXIT_BAR'
    end as status,
    case
        when exit_price is not null then 'synthetic_time_exit_available'
        else 'no_m5_bar_after_exit_horizon'
    end as reason,
    false,
    false
from matched
where rn = 1 or rn is null;
"""

REPORT = """
select
    exit_policy,
    count(*) as rows_count,
    count(*) filter (where status = 'EXIT_CANDIDATE') as exit_candidates,
    count(*) filter (where status = 'NO_EXIT_BAR') as no_exit_bar,
    round(sum(coalesce(pnl, 0)), 6) as total_pnl,
    round(avg(pnl), 6) as avg_pnl
from gold_synthetic_exit_policy_audit_v1
group by 1
order by exit_policy;
"""

def main() -> int:
    print("=== GOLD SYNTHETIC EXIT POLICY AUDIT V1 ===")
    print("mode=audit_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(INSERT)
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in rows:
        print(
            "GOLD_EXIT_POLICY_ROW "
            f"policy={r['exit_policy']} "
            f"rows={r['rows_count']} "
            f"exit_candidates={r['exit_candidates']} "
            f"no_exit_bar={r['no_exit_bar']} "
            f"total_pnl={r['total_pnl']} "
            f"avg_pnl={r['avg_pnl']} "
            "runtime_allow=0 execution_enabled=0"
        )

    print("GOLD_SYNTHETIC_EXIT_POLICY_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
