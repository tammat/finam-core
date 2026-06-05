#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


TARGET_UNIVERSE = [
    ("BTCUSD", "crypto", "research_only"),
    ("ETHUSD", "crypto", "research_only"),
    ("SPY", "us_etf", "research_only"),
    ("QQQ", "us_etf", "research_only"),
    ("GLD", "us_etf", "research_only"),
    ("SLV", "us_etf", "research_only"),
    ("EURUSD", "fx", "research_only"),
]

RECOMMENDED_TIMEFRAMES = ["M1", "M5", "M15"]


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main():
    print("=== RESEARCH UNIVERSE EXPANSION AUDIT V1 ===")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute("""
                select
                    symbol,
                    timeframe,
                    count(*) as bars,
                    min(ts) as first_ts,
                    max(ts) as last_ts
                from market_bars
                group by symbol, timeframe
                order by symbol, timeframe;
            """)
            current_rows = cur.fetchall()

            cur.execute("""
                select count(distinct symbol)
                from market_bars;
            """)
            current_symbols = cur.fetchone()[0]

    print("CURRENT_UNIVERSE")
    if not current_rows:
        print("CURRENT_ROW none")
    else:
        for symbol, timeframe, bars, first_ts, last_ts in current_rows:
            print(
                f"CURRENT_ROW symbol={symbol} timeframe={timeframe} "
                f"bars={bars} first_ts={first_ts} last_ts={last_ts}"
            )

    print()
    print("CURRENT_SYMBOLS_TOTAL", current_symbols)

    print()
    print("TARGET_UNIVERSE")
    for symbol, asset_class, mode in TARGET_UNIVERSE:
        print(f"TARGET_ROW symbol={symbol} asset_class={asset_class} mode={mode}")

    print()
    print("RECOMMENDED_TIMEFRAMES")
    for tf in RECOMMENDED_TIMEFRAMES:
        print(f"TIMEFRAME_ROW timeframe={tf}")

    print()
    print("ARCHITECTURE_LIMITS")
    print("LIMIT execution=disabled")
    print("LIMIT risk_stack=unchanged")
    print("LIMIT pipeline=unchanged")
    print("LIMIT storage=postgresql_only")
    print("LIMIT mode=research_only")

    print()
    print(f"ESTIMATED_TARGET_SYMBOLS={len(TARGET_UNIVERSE)}")
    print(f"ESTIMATED_TARGET_TIMEFRAMES={len(RECOMMENDED_TIMEFRAMES)}")
    print("VERDICT=READY_FOR_DATA_COLLECTION_AUDIT_ONLY")


if __name__ == "__main__":
    main()
