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
    print("=== CRYPTO FEATURE DASHBOARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    sql = """
        select
            symbol,
            timeframe,
            count(*) as rows,
            min(ts) as first_ts,
            max(ts) as last_ts,
            round(extract(epoch from (now() - max(ts))) / 60, 2) as lag_min,
            round(avg(atr_pct_14)::numeric, 8) as avg_atr_pct_14,
            round(avg(range_pct)::numeric, 8) as avg_range_pct,
            sum(case when compression_flag then 1 else 0 end) as compression_rows,
            sum(case when expansion_flag then 1 else 0 end) as expansion_rows,
            min(source) as source
        from research_feature_store
        where symbol in ('BTCUSD','ETHUSD')
        group by symbol, timeframe
        order by symbol, timeframe;
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    if not rows:
        print("FEATURE_ROW none")
        print("VERDICT=NO_CRYPTO_FEATURE_DATA")
        return

    total_rows = 0
    stale_rows = 0

    for row in rows:
        (
            symbol,
            timeframe,
            rows_count,
            first_ts,
            last_ts,
            lag_min,
            avg_atr_pct_14,
            avg_range_pct,
            compression_rows,
            expansion_rows,
            source,
        ) = row

        total_rows += int(rows_count)
        lag = float(lag_min or 0)
        if lag > 180:
            stale_rows += 1

        print(
            f"FEATURE_ROW symbol={symbol} timeframe={timeframe} "
            f"rows={rows_count} first_ts={first_ts} last_ts={last_ts} "
            f"lag_min={lag:.2f} avg_atr_pct_14={avg_atr_pct_14} "
            f"avg_range_pct={avg_range_pct} compression_rows={compression_rows} "
            f"expansion_rows={expansion_rows} source={source}"
        )

    print()
    print(f"TOTAL_FEATURE_ROWS={total_rows}")
    print(f"STALE_ROWS={stale_rows}")
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
