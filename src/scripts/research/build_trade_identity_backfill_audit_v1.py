#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists trade_identity_backfill_audit_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    trade_id bigint not null,
    symbol text not null,
    side text,
    qty numeric,
    price numeric,

    old_strategy text,
    old_timeframe text,
    new_strategy text not null,
    new_timeframe text not null,

    origin text,
    trade_source text,
    trade_created_at timestamptz,

    backfill_status text not null,
    backfill_reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false
);
"""

TRUNCATE = "truncate table trade_identity_backfill_audit_v1;"

INSERT = """
insert into trade_identity_backfill_audit_v1 (
    trade_id,
    symbol,
    side,
    qty,
    price,
    old_strategy,
    old_timeframe,
    new_strategy,
    new_timeframe,
    origin,
    trade_source,
    trade_created_at,
    backfill_status,
    backfill_reason,
    runtime_allowed,
    execution_enabled
)
select
    id as trade_id,
    symbol,
    side,
    qty,
    price,
    strategy as old_strategy,
    timeframe as old_timeframe,
    case
        when symbol = 'BRN6@RTSX' then 'BR_CONSERVATIVE_BREAKOUT'
        when symbol = 'NGN6@RTSX' then 'NG_CONSERVATIVE_BREAKOUT'
    end as new_strategy,
    'M5' as new_timeframe,
    origin,
    trade_source,
    created_at as trade_created_at,
    'PLANNED' as backfill_status,
    'missing_identity_for_clean_paper_whitelisted_symbol' as backfill_reason,
    false,
    false
from trades
where origin = 'paper'
  and trade_source = 'paper'
  and symbol in ('BRN6@RTSX', 'NGN6@RTSX')
  and coalesce(strategy, '') = ''
  and coalesce(timeframe, '') = ''
order by created_at;
"""

REPORT = """
select
    symbol,
    new_strategy,
    new_timeframe,
    count(*) as rows_count,
    min(trade_created_at) as first_trade,
    max(trade_created_at) as last_trade
from trade_identity_backfill_audit_v1
group by 1,2,3
order by rows_count desc;
"""

def main() -> int:
    print("=== TRADE IDENTITY BACKFILL AUDIT V1 ===")
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

    total = 0
    for r in rows:
        total += int(r["rows_count"])
        print(
            "TRADE_IDENTITY_BACKFILL_AUDIT_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['new_strategy']} "
            f"timeframe={r['new_timeframe']} "
            f"rows={r['rows_count']} "
            f"first={r['first_trade']} "
            f"last={r['last_trade']} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(f"TRADE_IDENTITY_BACKFILL_AUDIT_SUMMARY planned={total} runtime_allow=0 execution_enabled=0")
    print("TRADE_IDENTITY_BACKFILL_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
