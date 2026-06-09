#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ASSETS = {
    # Русский комментарий: USD ограничиваем валютными инструментами, чтобы BTCUSD/ETHUSD не попадали в USD-группу.
    "USD": ["USDRUBF@RTSX", "SI%@RTSX", "SI%", "%USDRUB%"],

    # Русский комментарий: золото на MOEX обычно идёт через GD-контракты и GLD/GOLD-тикеры.
    "GOLD": ["%GOLD%", "GD%@RTSX", "GD%", "GLD%", "GDU%", "GLDRUB%"],

    # Русский комментарий: BTCUSD должен относиться только к BTC, а не к USD.
    "BTC": ["BTCUSD", "BTCUSD@%", "%BTC%"],

    # Русский комментарий: ETH выводим отдельно, чтобы не загрязнять USD-группу.
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
)
SELECT
    asset,
    symbol,
    timeframe,
    COUNT(*) AS bars,
    MIN(ts) AS first_ts,
    MAX(ts) AS last_ts
FROM matched
GROUP BY asset, symbol, timeframe
ORDER BY asset, symbol, timeframe;
"""

def split_patterns(patterns: list[str]) -> tuple[list[str], list[str]]:
    exact, like = [], []
    for p in patterns:
        if "%" in p or "_" in p:
            like.append(p)
        else:
            exact.append(p)
    return exact, like

def readiness(bars: int) -> str:
    if bars <= 0:
        return "NO_DATA"
    if bars < 100:
        return "LOW_DATA"
    return "READY"

def main() -> None:
    print("=== CROSS ASSET MARKETDATA READINESS V1 ===")
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

    print("READINESS_ROWS")

    seen_assets = set()

    for r in all_rows:
        seen_assets.add(r["asset"])
        bars = int(r["bars"] or 0)

        print(
            "READINESS_ROW "
            f"asset={r['asset']} "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"bars={bars} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']} "
            f"status={readiness(bars)}"
        )

    for asset in ASSETS:
        if asset not in seen_assets:
            print(
                "READINESS_ROW "
                f"asset={asset} "
                "symbol=NONE "
                "timeframe=NONE "
                "bars=0 "
                "first_ts=None "
                "last_ts=None "
                "status=NO_DATA"
            )

    print()
    print("VERDICT=CROSS_ASSET_MARKETDATA_READINESS_RECORDED")
    print("CROSS_ASSET_MARKETDATA_READINESS_V1_OK")

if __name__ == "__main__":
    main()
