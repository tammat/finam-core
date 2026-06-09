#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOLS = [
    "GDM6@RTSX",
    "GDU6@RTSX",
    "GDZ6@RTSX",
]

SQL = """
SELECT
    symbol,
    timeframe,
    COUNT(*) AS bars,
    MIN(ts) AS first_ts,
    MAX(ts) AS last_ts
FROM market_bars
WHERE symbol = %(symbol)s
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe;
"""

def replay_status(bars: int) -> str:
    if bars < 100:
        return "INSUFFICIENT"
    if bars < 1000:
        return "LIMITED"
    return "READY"

def priority(symbol: str, bars: int) -> int:
    if symbol.startswith("GDM") and bars >= 1000:
        return 1
    if symbol.startswith("GDU") and bars >= 1000:
        return 2
    if bars >= 1000:
        return 10
    return 99

def main() -> None:
    print("=== GOLD RESEARCH REPLAY READINESS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("symbols=GDM6,GDU6,GDZ6")
    print()

    rows = []

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            for symbol in SYMBOLS:
                cur.execute(SQL, {"symbol": symbol})

                for row in cur.fetchall():
                    row = dict(row)

                    bars = int(row["bars"] or 0)

                    rows.append({
                        "symbol": row["symbol"],
                        "timeframe": row["timeframe"],
                        "bars": bars,
                        "first_ts": row["first_ts"],
                        "last_ts": row["last_ts"],
                        "status": replay_status(bars),
                        "priority": priority(row["symbol"], bars),
                    })

    print("REPLAY_ROWS")

    if not rows:
        print("NONE")

    rows.sort(
        key=lambda r: (
            r["priority"],
            r["symbol"],
            r["timeframe"],
        )
    )

    for r in rows:
        print(
            "REPLAY_ROW "
            f"priority={r['priority']} "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"bars={r['bars']} "
            f"status={r['status']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    ready = sum(1 for r in rows if r["status"] == "READY")

    print()
    print(f"READY_ROWS={ready}")
    print(f"TOTAL_ROWS={len(rows)}")
    print("VERDICT=GOLD_RESEARCH_REPLAY_READINESS_RECORDED")
    print("GOLD_RESEARCH_REPLAY_READINESS_V1_OK")

if __name__ == "__main__":
    main()
