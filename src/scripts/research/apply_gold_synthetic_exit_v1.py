#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
alter table gold_synthetic_exit_policy_audit_v1
add column if not exists synthetic_exit_trade_id bigint;
"""

APPLY_SQL = """
with candidates as (
    select
        entry_trade_id,
        symbol,
        strategy,
        timeframe,
        exit_ts,
        exit_price
    from gold_synthetic_exit_policy_audit_v1
    where exit_policy = 'TIME_EXIT_M5_12BARS'
      and status = 'EXIT_CANDIDATE'
      and symbol = 'GDU6@RTSX'
      and strategy = 'gold_short_only_shadow_v1'
      and timeframe = 'M5'
      and entry_side = 'SELL'
      and synthetic_exit_side = 'BUY'
      and runtime_allowed = false
      and execution_enabled = false
      and synthetic_exit_trade_id is null
),
inserted as (
    insert into trades (
        symbol,
        side,
        qty,
        price,
        commission,
        strategy,
        timeframe,
        origin,
        trade_source,
        created_at
    )
    select
        c.symbol,
        'BUY' as side,
        1.0 as qty,
        c.exit_price as price,
        0.0 as commission,
        c.strategy,
        c.timeframe,
        'paper' as origin,
        'paper' as trade_source,
        c.exit_ts as created_at
    from candidates c
    where not exists (
        select 1
        from trades t
        where t.symbol = c.symbol
          and t.strategy = c.strategy
          and t.timeframe = c.timeframe
          and t.side = 'BUY'
          and t.origin = 'paper'
          and t.trade_source = 'paper'
          and t.created_at = c.exit_ts
          and t.price = c.exit_price
    )
    returning id, symbol, strategy, timeframe, created_at, price
)
update gold_synthetic_exit_policy_audit_v1 a
set synthetic_exit_trade_id = i.id
from inserted i
where a.symbol = i.symbol
  and a.strategy = i.strategy
  and a.timeframe = i.timeframe
  and a.exit_ts = i.created_at
  and a.exit_price = i.price
  and a.exit_policy = 'TIME_EXIT_M5_12BARS'
returning i.id, i.symbol, i.strategy, i.timeframe, i.created_at, i.price;
"""

REPORT_SQL = """
select
    count(*) filter (where exit_policy='TIME_EXIT_M5_12BARS') as policy_rows,
    count(*) filter (where exit_policy='TIME_EXIT_M5_12BARS' and synthetic_exit_trade_id is not null) as applied_rows,
    count(*) filter (where exit_policy='TIME_EXIT_M5_12BARS' and synthetic_exit_trade_id is null) as pending_rows
from gold_synthetic_exit_policy_audit_v1;
"""

def main() -> int:
    print("=== GOLD SYNTHETIC EXIT APPLY V1 ===")
    print("mode=apply_synthetic_exits")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("policy=TIME_EXIT_M5_12BARS")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(APPLY_SQL)
            inserted = cur.fetchall()
            cur.execute(REPORT_SQL)
            report = cur.fetchone()
        conn.commit()

    print(f"GOLD_SYNTHETIC_EXIT_APPLIED rows={len(inserted)}")
    print(
        "GOLD_SYNTHETIC_EXIT_REPORT "
        f"policy_rows={report['policy_rows']} "
        f"applied_rows={report['applied_rows']} "
        f"pending_rows={report['pending_rows']} "
        "runtime_allow=0 execution_enabled=0"
    )
    print("GOLD_SYNTHETIC_EXIT_APPLY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
