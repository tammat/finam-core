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
WITH bars AS (
    SELECT
        symbol,
        COUNT(*) bars,
        MAX(ts) last_bar_ts
    FROM market_bars
    WHERE symbol = ANY(%s)
    GROUP BY symbol
),
sig AS (
    SELECT
        symbol,
        COUNT(*) signals,
        MAX(ts) last_signal_ts
    FROM signals
    WHERE symbol = ANY(%s)
    GROUP BY symbol
),
runtime AS (
    SELECT
        symbol,
        COUNT(*) runtime_rows
    FROM runtime_active_universe
    WHERE symbol = ANY(%s)
    GROUP BY symbol
)
SELECT
    s.symbol,
    COALESCE(b.bars,0) bars,
    b.last_bar_ts,
    COALESCE(g.signals,0) signals,
    g.last_signal_ts,
    COALESCE(r.runtime_rows,0) runtime_rows
FROM (
    SELECT unnest(%s::text[]) symbol
) s
LEFT JOIN bars b ON b.symbol=s.symbol
LEFT JOIN sig g ON g.symbol=s.symbol
LEFT JOIN runtime r ON r.symbol=s.symbol
ORDER BY s.symbol;
"""

def main():
    print("=== RUNTIME SHADOW CANDIDATE SIGNAL SOURCE AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                SQL,
                (
                    SYMBOLS,
                    SYMBOLS,
                    SYMBOLS,
                    SYMBOLS,
                ),
            )
            rows = cur.fetchall()

    print("SOURCE_ROWS")

    for r in rows:

        bars_ok = r["bars"] > 0
        signals_ok = r["signals"] > 0
        runtime_ok = r["runtime_rows"] > 0

        if not bars_ok:
            reason = "NO_MARKET_DATA"
        elif not runtime_ok:
            reason = "NOT_IN_RUNTIME_UNIVERSE"
        elif not signals_ok:
            reason = "NO_SIGNALS"
        else:
            reason = "SIGNALS_PRESENT"

        print(
            f"SOURCE_ROW "
            f"symbol={r['symbol']} "
            f"bars={r['bars']} "
            f"signals={r['signals']} "
            f"runtime_rows={r['runtime_rows']} "
            f"last_bar_ts={r['last_bar_ts']} "
            f"last_signal_ts={r['last_signal_ts']} "
            f"reason={reason}"
        )

    print()
    print("VERDICT=RUNTIME_SHADOW_CANDIDATE_SIGNAL_SOURCE_AUDIT_RECORDED")
    print("RUNTIME_SHADOW_CANDIDATE_SIGNAL_SOURCE_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
