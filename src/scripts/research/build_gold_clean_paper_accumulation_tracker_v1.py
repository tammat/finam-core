#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
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
    v3_net_pnl,
    accumulation_status,
    accumulation_reason
from clean_paper_accumulation_tracker_v1
where symbol in ('GDU6@RTSX', 'GDM6@RTSX')
   or strategy = 'gold_short_only_shadow_v1'
order by v3_full_chains desc, clean_trades desc;
"""

SHADOW_SQL = """
select
    symbol,
    strategy,
    timeframe,
    side,
    count(*) as shadow_signals
from runtime_shadow_gold_signals
group by 1,2,3,4
order by shadow_signals desc;
"""

def main() -> int:
    print("=== GOLD CLEAN PAPER ACCUMULATION TRACKER V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            clean_rows = cur.fetchall()

            cur.execute(SHADOW_SQL)
            shadow_rows = cur.fetchall()

    if not clean_rows:
        print(
            "GOLD_CLEAN_ACCUMULATION_STATUS=NO_CLEAN_PAPER_TRADES "
            "reason=gold_not_connected_to_paper_trades_yet"
        )
    else:
        for r in clean_rows:
            print(
                "GOLD_CLEAN_ACCUMULATION_ROW "
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
                "runtime_allow=0 execution_enabled=0"
            )

    for r in shadow_rows:
        print(
            "GOLD_SHADOW_REFERENCE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"side={r['side']} "
            f"shadow_signals={r['shadow_signals']}"
        )

    print("GOLD_CLEAN_PAPER_ACCUMULATION_TRACKER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
