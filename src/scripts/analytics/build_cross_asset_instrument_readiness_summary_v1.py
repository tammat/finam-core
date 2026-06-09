#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ASSETS = {
    "USD": ["USDRUBF@RTSX", "SI%@RTSX", "SI%", "%USDRUB%"],
    "GOLD": ["%GOLD%", "GD%@RTSX", "GD%", "GLD%", "GDU%", "GLDRUB%"],
    "BTC": ["BTCUSD", "BTCUSD@%", "%BTC%"],
    "ETH": ["ETHUSD", "ETHUSD@%", "%ETH%"],
}

SQL = """
WITH matched AS (
    SELECT
        %(asset)s::text AS asset,
        symbol,
        timeframe,
        ts
    FROM market_bars
    WHERE symbol = ANY(%(exact_symbols)s)
       OR symbol ILIKE ANY(%(like_patterns)s)
),
agg AS (
    SELECT
        asset,
        symbol,
        timeframe,
        COUNT(*) AS bars,
        MIN(ts) AS first_ts,
        MAX(ts) AS last_ts
    FROM matched
    GROUP BY asset, symbol, timeframe
)
SELECT *
FROM agg
ORDER BY asset, symbol, bars DESC;
"""

def split_patterns(patterns: list[str]) -> tuple[list[str], list[str]]:
    exact, like = [], []
    for p in patterns:
        if "%" in p or "_" in p:
            like.append(p)
        else:
            exact.append(p)
    return exact, like

def status(total_bars: int, best_bars: int) -> str:
    if total_bars <= 0:
        return "NO_DATA"
    if best_bars < 100:
        return "LOW_DATA"
    if best_bars < 1000:
        return "RESEARCH_READY"
    return "READY"

def priority(asset: str, total_bars: int, best_bars: int, symbol: str) -> int:
    if total_bars <= 0:
        return 99
    if asset == "GOLD" and symbol.startswith(("GDM", "GDU")) and best_bars >= 1000:
        return 1
    if asset == "USD" and symbol == "USDRUBF@RTSX" and best_bars >= 1000:
        return 2
    if asset == "BTC" and best_bars >= 1000:
        return 3
    if asset == "ETH" and best_bars >= 1000:
        return 4
    return 50

def main() -> None:
    print("=== CROSS ASSET INSTRUMENT READINESS SUMMARY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("assets=USD,GOLD,BTC,ETH")
    print()

    all_rows = []

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for asset, patterns in ASSETS.items():
                exact, like = split_patterns(patterns)
                cur.execute(
                    SQL,
                    {
                        "asset": asset,
                        "exact_symbols": exact or ["__NO_EXACT_MATCH__"],
                        "like_patterns": like or ["__NO_LIKE_MATCH__"],
                    },
                )
                all_rows.extend([dict(r) for r in cur.fetchall()])

    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in all_rows:
        grouped.setdefault((row["asset"], row["symbol"]), []).append(row)

    print("SUMMARY_ROWS")

    emitted_assets = set()

    summary = []
    for (asset, symbol), rows in grouped.items():
        emitted_assets.add(asset)
        total_bars = sum(int(r["bars"] or 0) for r in rows)
        best = max(rows, key=lambda r: int(r["bars"] or 0))
        best_bars = int(best["bars"] or 0)

        summary.append({
            "asset": asset,
            "symbol": symbol,
            "total_bars": total_bars,
            "best_timeframe": best["timeframe"],
            "best_bars": best_bars,
            "first_ts": min(r["first_ts"] for r in rows if r["first_ts"] is not None),
            "last_ts": max(r["last_ts"] for r in rows if r["last_ts"] is not None),
            "status": status(total_bars, best_bars),
            "priority": priority(asset, total_bars, best_bars, symbol),
        })

    for asset in ASSETS:
        if asset not in emitted_assets:
            summary.append({
                "asset": asset,
                "symbol": "NONE",
                "total_bars": 0,
                "best_timeframe": "NONE",
                "best_bars": 0,
                "first_ts": None,
                "last_ts": None,
                "status": "NO_DATA",
                "priority": 99,
            })

    summary = sorted(summary, key=lambda r: (r["priority"], r["asset"], r["symbol"]))

    for r in summary:
        print(
            "SUMMARY_ROW "
            f"priority={r['priority']} "
            f"asset={r['asset']} "
            f"symbol={r['symbol']} "
            f"status={r['status']} "
            f"total_bars={r['total_bars']} "
            f"best_timeframe={r['best_timeframe']} "
            f"best_bars={r['best_bars']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("VERDICT=CROSS_ASSET_INSTRUMENT_READINESS_SUMMARY_RECORDED")
    print("CROSS_ASSET_INSTRUMENT_READINESS_SUMMARY_V1_OK")

if __name__ == "__main__":
    main()
