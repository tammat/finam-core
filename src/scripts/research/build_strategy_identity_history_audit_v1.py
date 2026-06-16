#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2
import psycopg2.extras

SQL = """
select
    a.symbol,
    a.strategy,
    a.timeframe,
    a.trade_source,
    count(*) as trades,
    count(distinct c.entry_ts::date) as entry_days,
    count(distinct c.exit_ts::date) as exit_days,
    min(c.entry_ts) as first_entry,
    max(c.entry_ts) as last_entry,
    min(c.exit_ts) as first_exit,
    max(c.exit_ts) as last_exit,
    count(*) filter (where a.attribution_quality='FULL') as full_ctx,
    count(*) filter (where a.attribution_quality='PARTIAL') as partial_ctx,
    count(*) filter (where a.attribution_quality='RISK_CONTEXT_WEAK') as weak_ctx,
    sum(a.pnl) as pnl,
    avg(a.pnl) as expectancy
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id=a.closed_trade_id
where a.symbol=%s
  and a.strategy=%s
  and a.timeframe=%s
group by a.symbol,a.strategy,a.timeframe,a.trade_source;
"""

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--strategy", required=True)
    p.add_argument("--timeframe", required=True)
    args = p.parse_args()

    print("=== STRATEGY IDENTITY HISTORY AUDIT V1 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (args.symbol, args.strategy, args.timeframe))
            rows = cur.fetchall()

    for r in rows:
        trades = int(r["trades"] or 0)
        entry_days = int(r["entry_days"] or 0)
        exit_days = int(r["exit_days"] or 0)

        reason = "ok"
        status = "IDENTITY_REVIEW"
        if trades >= 100 and (entry_days < 10 or exit_days < 10):
            status = "BACKFILL_OR_RECONSTRUCTION_ARTIFACT_SUSPECT"
            reason = "many_trades_low_time_diversity"

        print(
            "IDENTITY_HISTORY_ROW "
            f"symbol={r['symbol']} strategy={r['strategy']} timeframe={r['timeframe']} "
            f"trades={trades} entry_days={entry_days} exit_days={exit_days} "
            f"full_ctx={int(r['full_ctx'] or 0)} partial_ctx={int(r['partial_ctx'] or 0)} "
            f"weak_ctx={int(r['weak_ctx'] or 0)} "
            f"pnl={float(r['pnl'] or 0):.4f} expectancy={float(r['expectancy'] or 0):.6f} "
            f"first_entry={r['first_entry']} last_entry={r['last_entry']} "
            f"first_exit={r['first_exit']} last_exit={r['last_exit']} "
            f"status={status} reason={reason}"
        )

    print("STRATEGY_IDENTITY_HISTORY_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
