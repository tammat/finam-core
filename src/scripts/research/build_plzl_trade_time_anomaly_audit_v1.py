#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "PLZL@MISX"

SQL = """
select
    a.strategy,
    a.timeframe,
    count(*) as trades,
    min(c.entry_ts) as first_entry,
    max(c.entry_ts) as last_entry,
    min(c.exit_ts) as first_exit,
    max(c.exit_ts) as last_exit,
    count(distinct c.entry_ts::date) as entry_days,
    count(distinct c.exit_ts::date) as exit_days,
    count(distinct c.entry_ts) as distinct_entry_ts,
    count(distinct c.exit_ts) as distinct_exit_ts,
    sum(a.pnl)::float as pnl,
    avg(a.pnl)::float as expectancy
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id = a.closed_trade_id
where a.symbol=%s
  and a.strategy in ('MOEX_SIMPLE_MOMENTUM','MOEX_MEAN_REVERSION_V1')
  and a.timeframe='D1'
  and a.trade_source='paper'
group by a.strategy, a.timeframe
order by a.strategy;
"""

def main() -> int:
    print("=== PLZL TRADE TIME ANOMALY AUDIT V1 ===")
    print("mode=research_only")
    print("execution_enabled=0")

    anomaly_rows = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL,))
            rows = cur.fetchall()

    for r in rows:
        exit_days = int(r["exit_days"] or 0)
        entry_days = int(r["entry_days"] or 0)

        status = "OK"
        reason = "time_distribution_ok"

        if exit_days <= 1 and int(r["trades"] or 0) >= 30:
            status = "TIME_ANOMALY"
            reason = "many_trades_closed_on_single_exit_day"
            anomaly_rows += 1

        print(
            "PLZL_TIME_AUDIT_ROW "
            f"symbol={SYMBOL} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"trades={r['trades']} "
            f"entry_days={entry_days} "
            f"exit_days={exit_days} "
            f"distinct_entry_ts={r['distinct_entry_ts']} "
            f"distinct_exit_ts={r['distinct_exit_ts']} "
            f"first_entry={r['first_entry']} "
            f"last_entry={r['last_entry']} "
            f"first_exit={r['first_exit']} "
            f"last_exit={r['last_exit']} "
            f"pnl={float(r['pnl'] or 0):.4f} "
            f"expectancy={float(r['expectancy'] or 0):.4f} "
            f"status={status} "
            f"reason={reason}",
            flush=True,
        )

    print(
        "PLZL_TRADE_TIME_ANOMALY_AUDIT_SUMMARY "
        f"rows={len(rows)} "
        f"anomaly_rows={anomaly_rows} "
        "runtime_allow=0 execution_enabled=0",
        flush=True,
    )

    print("PLZL_TRADE_TIME_ANOMALY_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
