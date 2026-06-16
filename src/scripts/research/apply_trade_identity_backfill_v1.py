#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

APPLY = """
with approved as (
    select
        trade_id,
        new_strategy,
        new_timeframe
    from trade_identity_backfill_audit_v1
    where backfill_status = 'PLANNED'
      and symbol in ('BRN6@RTSX', 'NGN6@RTSX')
      and new_strategy in ('BR_CONSERVATIVE_BREAKOUT', 'NG_CONSERVATIVE_BREAKOUT')
      and new_timeframe = 'M5'
      and runtime_allowed = false
      and execution_enabled = false
)
update trades t
set
    strategy = a.new_strategy,
    timeframe = a.new_timeframe
from approved a
where t.id = a.trade_id
  and t.origin = 'paper'
  and t.trade_source = 'paper'
  and t.symbol in ('BRN6@RTSX', 'NGN6@RTSX')
  and coalesce(t.strategy, '') = ''
  and coalesce(t.timeframe, '') = ''
returning t.id, t.symbol, t.strategy, t.timeframe;
"""

MARK_DONE = """
update trade_identity_backfill_audit_v1 a
set backfill_status = 'APPLIED'
where exists (
    select 1
    from trades t
    where t.id = a.trade_id
      and t.strategy = a.new_strategy
      and t.timeframe = a.new_timeframe
)
and a.backfill_status = 'PLANNED';
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    count(*) as rows_count
from trades
where origin='paper'
  and trade_source='paper'
  and symbol in ('BRN6@RTSX', 'NGN6@RTSX')
  and strategy in ('BR_CONSERVATIVE_BREAKOUT', 'NG_CONSERVATIVE_BREAKOUT')
  and timeframe='M5'
group by 1,2,3
order by rows_count desc;
"""

def main() -> int:
    print("=== TRADE IDENTITY BACKFILL V1 ===")
    print("mode=apply_backfill")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(APPLY)
            applied = cur.fetchall()
            cur.execute(MARK_DONE)
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    print(f"TRADE_IDENTITY_BACKFILL_APPLIED rows={len(applied)} runtime_allow=0 execution_enabled=0")

    for r in rows:
        print(
            "TRADE_IDENTITY_BACKFILL_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"rows={r['rows_count']}"
        )

    print("TRADE_IDENTITY_BACKFILL_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
