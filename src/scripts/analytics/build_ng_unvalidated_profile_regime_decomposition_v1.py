#!/usr/bin/env python3

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SQL = """
select
    coalesce(
        payload->'entry_payload'->'features'->>'regime',
        'UNKNOWN'
    ) as regime,

    coalesce(
        payload->'entry_payload'
               ->'trade_context_snapshot'
               ->'edge_gate'
               ->>'reason',
        'UNKNOWN'
    ) as edge_gate_reason,

    count(*) trades,

    round(sum(net_pnl)::numeric,6) net_pnl,

    round(avg(net_pnl)::numeric,6) expectancy,

    round(
        100.0 *
        sum(case when net_pnl > 0 then 1 else 0 end)
        / nullif(count(*),0),
        2
    ) as winrate

from closed_trades
where root_symbol='NG'
  and source='closed_trade_engine_v1_1'
group by 1,2
order by net_pnl asc;
"""

def main():
    print("=== NG UNVALIDATED PROFILE REGIME DECOMPOSITION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    conn = psycopg2.connect(DATABASE_URL)

    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)

            rows = cur.fetchall()

            print("REGIME_EDGE_SUMMARY")

            total = 0.0

            for r in rows:
                total += float(r["net_pnl"])

                print(
                    "REGIME_EDGE_ROW "
                    f"regime={r['regime']} "
                    f"edge_gate_reason={r['edge_gate_reason']} "
                    f"trades={r['trades']} "
                    f"net_pnl={r['net_pnl']} "
                    f"expectancy={r['expectancy']} "
                    f"winrate={r['winrate']}"
                )

            print()
            print(f"TOTAL_NET_PNL={round(total,6)}")
            print(f"ROWS={len(rows)}")
            print("VERDICT=NG_REGIME_EDGE_DECOMPOSED")

if __name__ == "__main__":
    main()
