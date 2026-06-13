#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOLS = [
    "USDRUBF@RTSX",
    "LKOH@MISX",
]

SQL = """
SELECT
    symbol,
    COUNT(*) bars,
    MIN(ts) first_bar_ts,
    MAX(ts) last_bar_ts,
    ROUND(
        EXTRACT(EPOCH FROM (MAX(ts)-MIN(ts)))
        / 86400.0,
        2
    ) days_covered,
    ROUND(
        AVG(
            CASE
                WHEN open > 0
                THEN ABS(high-low)/open*100
                ELSE NULL
            END
        )::numeric,
        4
    ) avg_bar_range_pct
FROM market_bars
WHERE symbol = ANY(%s)
GROUP BY symbol
ORDER BY symbol;
"""

def main():
    print("=== INSTRUMENT RESEARCH CANDIDATE AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(SQL, (SYMBOLS,))
            rows = cur.fetchall()

    print("INSTRUMENT_ROWS")

    for r in rows:

        bars = int(r["bars"] or 0)
        atr_proxy = float(r["avg_bar_range_pct"] or 0)

        if bars > 5000 and atr_proxy > 0.20:
            verdict = "RESEARCH_CANDIDATE"
        elif bars > 5000:
            verdict = "WATCH"
        else:
            verdict = "REJECT"

        print(
            f"INSTRUMENT_ROW "
            f"symbol={r['symbol']} "
            f"bars={bars} "
            f"days_covered={r['days_covered']} "
            f"avg_bar_range_pct={atr_proxy} "
            f"first_bar_ts={r['first_bar_ts']} "
            f"last_bar_ts={r['last_bar_ts']} "
            f"verdict={verdict}"
        )

    print()
    print("VERDICT=INSTRUMENT_RESEARCH_CANDIDATE_AUDIT_RECORDED")
    print("INSTRUMENT_RESEARCH_CANDIDATE_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
