#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def main():
    print("=== BR SHORT SHADOW EFFECTIVENESS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        cur.execute("""
            SELECT
                symbol,
                count(*) AS trades,
                round(sum(net_pnl)::numeric, 6) AS net_pnl,
                round(avg(net_pnl)::numeric, 6) AS expectancy,
                count(*) FILTER (WHERE net_pnl > 0) AS wins,
                count(*) FILTER (WHERE net_pnl <= 0) AS losses
            FROM closed_trades
            WHERE source='closed_trade_engine_v1_1'
              AND (
                    root_symbol='BR'
                    OR symbol LIKE 'BR%%'
                  )
              AND upper(side)='SHORT'
            GROUP BY symbol
            ORDER BY symbol;
        """)

        rows = cur.fetchall()

        print("SHORT_RESULTS")

        total_trades = 0
        total_pnl = 0.0

        for r in rows:
            total_trades += int(r["trades"])
            total_pnl += float(r["net_pnl"] or 0)

            print(
                f"SHORT_ROW "
                f"symbol={r['symbol']} "
                f"trades={r['trades']} "
                f"wins={r['wins']} "
                f"losses={r['losses']} "
                f"net_pnl={r['net_pnl']} "
                f"expectancy={r['expectancy']}"
            )

        print()
        print("SUMMARY")
        print(f"TOTAL_SHORT_TRADES={total_trades}")
        print(f"TOTAL_SHORT_NET_PNL={round(total_pnl,6)}")

        if total_trades < 20:
            verdict = "INSUFFICIENT_LIVE_DATA"
        elif total_pnl > 0:
            verdict = "PROMISING"
        else:
            verdict = "NEGATIVE"

        print(f"VERDICT={verdict}")
        print("BR_SHORT_SHADOW_EFFECTIVENESS_V1_OK")


if __name__ == "__main__":
    main()
