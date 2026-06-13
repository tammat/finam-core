#!/usr/bin/env python3

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SQL = """
select
    coalesce(
        payload->'entry_payload'->>'reason',
        payload->'entry_payload'->>'source',
        payload->'entry_payload'->>'strategy',
        payload->>'entry_reason',
        payload->>'intent_reason',
        payload->>'reason',
        'UNKNOWN'
    ) as entry_reason,
    count(*) trades,
    round(sum(net_pnl)::numeric,6) net_pnl,
    round(avg(net_pnl)::numeric,6) expectancy,
    round(
        100.0 *
        sum(case when net_pnl > 0 then 1 else 0 end)
        / nullif(count(*),0),
        2
    ) winrate
from closed_trades
where root_symbol='NG'
  and source='closed_trade_engine_v1_1'
group by 1
order by net_pnl desc;
"""

def main():
    print("=== NG SIGNAL QUALITY DECOMPOSITION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")

    conn = psycopg2.connect(DATABASE_URL)

    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)

            rows = cur.fetchall()

            print()
            print("ENTRY_REASON_SUMMARY")

            for r in rows:
                print(
                    "ENTRY_REASON_ROW "
                    f"entry_reason={r['entry_reason']} "
                    f"trades={r['trades']} "
                    f"net_pnl={r['net_pnl']} "
                    f"expectancy={r['expectancy']} "
                    f"winrate={r['winrate']}"
                )

            print()
            print(f"SUMMARY_ROWS={len(rows)}")
            print("VERDICT=NG_SIGNAL_QUALITY_DECOMPOSED")

if __name__ == "__main__":
    main()
