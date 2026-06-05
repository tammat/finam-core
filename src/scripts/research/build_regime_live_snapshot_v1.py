#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

SYMBOLS = [
    "BRN6@RTSX",
    "NGN6@RTSX",
    "USDRUBF@RTSX",
    "BTCUSD",
    "ETHUSD",
]


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def classify(compression, expansion):
    if expansion:
        return "EXPANSION"
    if compression:
        return "COMPRESSION"
    return "MIXED"


def main():
    print("=== REGIME LIVE SNAPSHOT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    sql = """
    select distinct on (symbol)
        symbol,
        timeframe,
        ts,
        compression_flag,
        expansion_flag,
        atr_pct_14,
        momentum_20
    from research_feature_store
    where timeframe='M5'
      and symbol = any(%s)
    order by symbol, ts desc
    """

    snapshot = {}

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, (SYMBOLS,))
            rows = cur.fetchall()

    for symbol, tf, ts, compression, expansion, atr, momentum in rows:
        regime = classify(compression, expansion)

        snapshot[symbol] = regime

        print(
            f"SNAPSHOT_ROW symbol={symbol} "
            f"timeframe={tf} "
            f"regime={regime} "
            f"atr_pct_14={float(atr or 0):.8f} "
            f"momentum_20={float(momentum or 0):.8f} "
            f"ts={ts}"
        )

    print()

    key = (
        f"BR={snapshot.get('BRN6@RTSX','NA')}"
        f"|NG={snapshot.get('NGN6@RTSX','NA')}"
        f"|USD={snapshot.get('USDRUBF@RTSX','NA')}"
        f"|BTC={snapshot.get('BTCUSD','NA')}"
        f"|ETH={snapshot.get('ETHUSD','NA')}"
    )

    print(f"LIVE_REGIME_KEY={key}")
    print(f"SYMBOLS_FOUND={len(snapshot)}")
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
