#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists gold_shadow_to_paper_accumulation_audit_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    shadow_signal_id bigint,
    symbol text not null,
    strategy text not null,
    timeframe text not null,
    side text not null,
    price numeric,
    signal_ts timestamptz,

    action text not null,
    reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,
    paper_trade_id bigint
);
"""

AUDIT_SQL = """
select
    id as shadow_signal_id,
    symbol,
    strategy,
    timeframe,
    side,
    entry_price as price,
    signal_ts
from runtime_shadow_gold_signals
where symbol = 'GDU6@RTSX'
  and strategy = 'gold_short_only_shadow_v1'
  and timeframe = 'M5'
  and side = 'SELL'
order by created_at;
"""

INSERT_AUDIT = """
insert into gold_shadow_to_paper_accumulation_audit_v1 (
    shadow_signal_id,
    symbol,
    strategy,
    timeframe,
    side,
    price,
    signal_ts,
    action,
    reason,
    runtime_allowed,
    execution_enabled
)
values (
    %(shadow_signal_id)s,
    %(symbol)s,
    %(strategy)s,
    %(timeframe)s,
    %(side)s,
    %(price)s,
    %(signal_ts)s,
    %(action)s,
    %(reason)s,
    false,
    false
);
"""

APPLY_SQL = """
with inserted as (
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
        a.symbol,
        a.side,
        1.0 as qty,
        a.price,
        0.0 as commission,
        a.strategy,
        a.timeframe,
        'paper' as origin,
        'paper' as trade_source,
        a.signal_ts as created_at
    from gold_shadow_to_paper_accumulation_audit_v1 a
    where a.action = 'CREATE_PAPER_TRADE'
      and a.runtime_allowed = false
      and a.execution_enabled = false
      and a.paper_trade_id is null
      and not exists (
          select 1
          from trades t
          where t.symbol = a.symbol
            and t.strategy = a.strategy
            and t.timeframe = a.timeframe
            and t.side = a.side
            and t.origin = 'paper'
            and t.trade_source = 'paper'
            and t.created_at = a.signal_ts
      )
    returning id, symbol, strategy, timeframe, side, price, created_at
)
update gold_shadow_to_paper_accumulation_audit_v1 a
set paper_trade_id = i.id
from inserted i
where a.symbol = i.symbol
  and a.strategy = i.strategy
  and a.timeframe = i.timeframe
  and a.side = i.side
  and a.signal_ts = i.created_at
returning i.id, i.symbol, i.strategy, i.timeframe, i.side, i.price;
"""

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()

    print("=== GOLD SHADOW TO PAPER ACCUMULATOR V1 ===")
    print("mode=audit_only" if args.audit_only else "mode=apply_paper_accumulation")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)

            cur.execute("truncate table gold_shadow_to_paper_accumulation_audit_v1;")
            cur.execute(AUDIT_SQL)
            signals = cur.fetchall()

            for s in signals:
                if not s["price"]:
                    action = "BLOCK"
                    reason = "missing_price"
                else:
                    action = "CREATE_PAPER_TRADE"
                    reason = "gdu6_gold_short_only_shadow_to_paper"

                cur.execute(
                    INSERT_AUDIT,
                    {
                        **s,
                        "action": action,
                        "reason": reason,
                    },
                )

            inserted = []
            if not args.audit_only:
                cur.execute(APPLY_SQL)
                inserted = cur.fetchall()

        conn.commit()

    print(f"GOLD_ACCUMULATION_AUDIT_SIGNALS total={len(signals)}")
    print(f"GOLD_ACCUMULATION_PAPER_TRADES_INSERTED rows={len(inserted)}")

    print("GOLD_SHADOW_TO_PAPER_ACCUMULATOR_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
