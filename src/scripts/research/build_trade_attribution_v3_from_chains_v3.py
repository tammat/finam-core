#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists trade_attribution_v3 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    chain_v3_id bigint not null references closed_trade_chains_v3(id),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    entry_ts timestamptz not null,
    exit_ts timestamptz not null,

    side text not null,
    qty numeric not null,

    entry_price numeric not null,
    exit_price numeric not null,

    gross_pnl numeric not null,
    net_pnl numeric not null,

    attribution_quality text not null,
    attribution_reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(chain_v3_id)
);
"""

TRUNCATE = "truncate table trade_attribution_v3;"

INSERT = """
insert into trade_attribution_v3 (
    chain_v3_id,
    symbol,
    strategy,
    timeframe,
    trade_source,
    entry_ts,
    exit_ts,
    side,
    qty,
    entry_price,
    exit_price,
    gross_pnl,
    net_pnl,
    attribution_quality,
    attribution_reason,
    runtime_allowed,
    execution_enabled
)
select
    c.id,
    c.symbol,
    c.strategy,
    c.timeframe,
    c.trade_source,
    c.entry_ts,
    c.exit_ts,
    c.side,
    c.qty,
    c.entry_price,
    c.exit_price,
    c.gross_pnl,
    c.net_pnl,
    case
        when c.quality_status='FULL'
            then 'FULL'
        when c.quality_status='PARTIAL'
            then 'PARTIAL'
        else 'UNSUPPORTED'
    end as attribution_quality,
    'from_closed_trade_chains_v3:' || c.quality_reason,
    false,
    false
from closed_trade_chains_v3 c
where coalesce(c.strategy,'') <> ''
  and coalesce(c.timeframe,'') <> ''
  and c.quality_status in ('FULL','PARTIAL')
on conflict(chain_v3_id) do nothing;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    count(*) as rows,
    count(*) filter (where attribution_quality='FULL') as full_rows,
    count(*) filter (where attribution_quality='PARTIAL') as partial_rows,
    count(distinct entry_ts::date) as entry_days,
    count(distinct exit_ts::date) as exit_days,
    coalesce(sum(net_pnl),0) as net_pnl
from trade_attribution_v3
group by symbol,strategy,timeframe,trade_source
order by symbol,strategy,timeframe;
"""

SUMMARY = """
select
    count(*) as total,
    count(*) filter (where attribution_quality='FULL') as full_rows,
    count(*) filter (where attribution_quality='PARTIAL') as partial_rows,
    count(*) filter (where attribution_quality='UNSUPPORTED') as unsupported_rows
from trade_attribution_v3;
"""

def main() -> int:
    print("=== TRADE ATTRIBUTION V3 FROM CHAINS V3 ===")
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
            "TRADE_ATTRIBUTION_V3_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"rows={r['rows']} "
            f"full={r['full_rows']} "
            f"partial={r['partial_rows']} "
            f"entry_days={r['entry_days']} "
            f"exit_days={r['exit_days']} "
            f"net_pnl={float(r['net_pnl'] or 0):.6f} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "TRADE_ATTRIBUTION_V3_SUMMARY "
        f"total={summary['total']} "
        f"full={summary['full_rows']} "
        f"partial={summary['partial_rows']} "
        f"unsupported={summary['unsupported_rows']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("TRADE_ATTRIBUTION_V3_FROM_CHAINS_V3_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
