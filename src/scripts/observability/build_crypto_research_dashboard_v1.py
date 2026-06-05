#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main() -> None:
    print("=== CRYPTO RESEARCH DASHBOARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    sql = """
        select
            symbol,
            timeframe,
            count(*) as bars,
            min(ts) as first_ts,
            max(ts) as last_ts,
            round(extract(epoch from (now() - max(ts))) / 60, 2) as lag_min,
            min(source) as source
        from market_bars
        where symbol in ('BTCUSD','ETHUSD')
          and source = 'binance_public_klines'
        group by symbol, timeframe
        order by symbol, timeframe;
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    if not rows:
        print("CRYPTO_ROW none")
        print("VERDICT=NO_CRYPTO_RESEARCH_DATA")
        return

    total_bars = 0
    stale_rows = 0

    for symbol, timeframe, bars, first_ts, last_ts, lag_min, source in rows:
        total_bars += int(bars)

        lag = float(lag_min or 0)
        if lag > 180:
            stale_rows += 1

        print(
            f"CRYPTO_ROW symbol={symbol} timeframe={timeframe} "
            f"bars={bars} first_ts={first_ts} last_ts={last_ts} "
            f"lag_min={lag:.2f} source={source}"
        )

    print()
    print(f"TOTAL_CRYPTO_BARS={total_bars}")
    print(f"STALE_ROWS={stale_rows}")
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
