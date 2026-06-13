#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


SYMBOLS = ["BRN6@RTSX", "NGN6@RTSX", "USDRUBF@RTSX", "BTCUSD", "ETHUSD"]
TIMEFRAMES = ["M1", "M5"]


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main() -> None:
    print("=== CROSS MARKET REGIME RESEARCH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    sql = """
        select
            symbol,
            timeframe,
            count(*) as rows,
            round(avg(atr_pct_14)::numeric, 8) as avg_atr_pct_14,
            round(avg(range_pct)::numeric, 8) as avg_range_pct,
            round(avg(momentum_20)::numeric, 8) as avg_momentum_20,
            sum(case when compression_flag then 1 else 0 end) as compression_rows,
            sum(case when expansion_flag then 1 else 0 end) as expansion_rows,
            round(
                sum(case when compression_flag then 1 else 0 end)::numeric
                / nullif(count(*), 0),
                4
            ) as compression_rate,
            round(
                sum(case when expansion_flag then 1 else 0 end)::numeric
                / nullif(count(*), 0),
                4
            ) as expansion_rate,
            max(ts) as last_ts
        from research_feature_store
        where symbol = any(%s)
          and timeframe = any(%s)
        group by symbol, timeframe
        order by symbol, timeframe;
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, (SYMBOLS, TIMEFRAMES))
            rows = cur.fetchall()

    if not rows:
        print("REGIME_ROW none")
        print("VERDICT=NO_FEATURE_DATA")
        return

    compression_leaders = []
    expansion_leaders = []

    for row in rows:
        (
            symbol,
            timeframe,
            rows_count,
            avg_atr_pct_14,
            avg_range_pct,
            avg_momentum_20,
            compression_rows,
            expansion_rows,
            compression_rate,
            expansion_rate,
            last_ts,
        ) = row

        compression_rate_f = float(compression_rate or 0)
        expansion_rate_f = float(expansion_rate or 0)

        compression_leaders.append((compression_rate_f, symbol, timeframe))
        expansion_leaders.append((expansion_rate_f, symbol, timeframe))

        if compression_rate_f >= 0.70:
            regime_bias = "COMPRESSION_DOMINANT"
        elif expansion_rate_f >= 0.15:
            regime_bias = "EXPANSION_ACTIVE"
        else:
            regime_bias = "MIXED"

        print(
            f"REGIME_ROW symbol={symbol} timeframe={timeframe} rows={rows_count} "
            f"avg_atr_pct_14={avg_atr_pct_14} avg_range_pct={avg_range_pct} "
            f"avg_momentum_20={avg_momentum_20} compression_rows={compression_rows} "
            f"expansion_rows={expansion_rows} compression_rate={compression_rate} "
            f"expansion_rate={expansion_rate} regime_bias={regime_bias} last_ts={last_ts}"
        )

    compression_leaders.sort(reverse=True)
    expansion_leaders.sort(reverse=True)

    print()
    print("TOP_COMPRESSION")
    for rate, symbol, timeframe in compression_leaders[:5]:
        print(f"TOP_COMPRESSION_ROW symbol={symbol} timeframe={timeframe} compression_rate={rate:.4f}")

    print()
    print("TOP_EXPANSION")
    for rate, symbol, timeframe in expansion_leaders[:5]:
        print(f"TOP_EXPANSION_ROW symbol={symbol} timeframe={timeframe} expansion_rate={rate:.4f}")

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
