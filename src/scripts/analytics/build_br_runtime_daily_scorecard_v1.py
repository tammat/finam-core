#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SQL = """
select
    count(*) as trades,
    round(coalesce(sum(net_pnl),0)::numeric,6) as net_pnl,
    round(coalesce(avg(net_pnl),0)::numeric,6) as expectancy,
    round(
        100.0 * sum(case when net_pnl > 0 then 1 else 0 end) / nullif(count(*),0),
        2
    ) as winrate,
    round(coalesce(sum(case when net_pnl > 0 then net_pnl else 0 end),0)::numeric,6) as gross_profit,
    round(coalesce(abs(sum(case when net_pnl < 0 then net_pnl else 0 end)),0)::numeric,6) as gross_loss
from closed_trades
where root_symbol='BR'
  and source='closed_trade_engine_v1_1'
  and coalesce(exit_ts, closed_at, created_at) >= current_date;
"""

DETAIL_SQL = """
select
    symbol,
    side,
    coalesce(payload->>'exit_reason','UNKNOWN') as exit_reason,
    count(*) as trades,
    round(sum(net_pnl)::numeric,6) as net_pnl,
    round(avg(net_pnl)::numeric,6) as expectancy
from closed_trades
where root_symbol='BR'
  and source='closed_trade_engine_v1_1'
  and coalesce(exit_ts, closed_at, created_at) >= current_date
group by symbol, side, coalesce(payload->>'exit_reason','UNKNOWN')
order by net_pnl desc;
"""

def main() -> None:
    print("=== BR RUNTIME DAILY SCORECARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=today")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            summary = cur.fetchone()

            cur.execute(DETAIL_SQL)
            detail = cur.fetchall()

    print("BR_DAILY_SUMMARY")
    print(
        "SUMMARY_ROW "
        f"trades={summary['trades']} "
        f"net_pnl={summary['net_pnl']} "
        f"expectancy={summary['expectancy']} "
        f"winrate={summary['winrate']} "
        f"gross_profit={summary['gross_profit']} "
        f"gross_loss={summary['gross_loss']}"
    )
    print()

    print("BR_DAILY_DETAIL")
    if not detail:
        print("NONE")
    for r in detail:
        print(
            "DETAIL_ROW "
            f"symbol={r['symbol']} side={r['side']} "
            f"exit_reason={r['exit_reason']} "
            f"trades={r['trades']} "
            f"net_pnl={r['net_pnl']} "
            f"expectancy={r['expectancy']}"
        )

    print()
    print("VERDICT=BR_RUNTIME_DAILY_SCORECARD_RECORDED")
    print("BR_RUNTIME_DAILY_SCORECARD_V1_OK")


if __name__ == "__main__":
    main()
