# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import argparse
import psycopg2


def dsn() -> str:
    return os.getenv("DATABASE_URL") or (
        f"postgresql://{os.getenv('DB_USER','finam')}:{os.getenv('DB_PASSWORD','finam')}"
        f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','finam')}"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--timeframe", default="M1")
    p.add_argument("--max-gap-min", type=int, default=3)
    p.add_argument("--max-zero-volume-pct", type=float, default=50.0)
    args = p.parse_args()

    errors = []

    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*), min(ts), max(ts)
                FROM market_data
                WHERE symbol=%s AND timeframe=%s
            """, (args.symbol, args.timeframe))
            bars_count, min_ts, max_ts = cur.fetchone()

            cur.execute("""
                SELECT count(*)
                FROM market_ticks
                WHERE symbol=%s
            """, (args.symbol,))
            ticks_count = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM market_data
                WHERE symbol=%s AND timeframe=%s AND volume = 0
            """, (args.symbol, args.timeframe))
            zero_volume = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM (
                    SELECT symbol, timeframe, ts, count(*)
                    FROM market_data
                    WHERE symbol=%s AND timeframe=%s
                    GROUP BY symbol, timeframe, ts
                    HAVING count(*) > 1
                ) d
            """, (args.symbol, args.timeframe))
            duplicates = cur.fetchone()[0]

            cur.execute("""
                WITH x AS (
                    SELECT
                        ts,
                        lag(ts) OVER (ORDER BY ts) AS prev_ts
                    FROM market_data
                    WHERE symbol=%s AND timeframe=%s
                )
                SELECT count(*)
                FROM x
                WHERE prev_ts IS NOT NULL
                  AND EXTRACT(EPOCH FROM (ts - prev_ts)) / 60.0 > %s
            """, (args.symbol, args.timeframe, args.max_gap_min))
            gaps = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM market_data
                WHERE symbol=%s AND timeframe=%s
                  AND (
                      close_price <= 0
                      OR high < low
                      OR open IS NULL
                      OR high IS NULL
                      OR low IS NULL
                  )
            """, (args.symbol, args.timeframe))
            bad_prices = cur.fetchone()[0]

    zero_pct = (zero_volume / bars_count * 100.0) if bars_count else 0.0

    if bars_count == 0:
        errors.append("NO_BARS")
    if ticks_count == 0:
        errors.append("NO_TICKS")
    if duplicates > 0:
        errors.append(f"DUPLICATES={duplicates}")
    if gaps > 0:
        errors.append(f"GAPS={gaps}")
    if bad_prices > 0:
        errors.append(f"BAD_PRICES={bad_prices}")
    if zero_pct > args.max_zero_volume_pct:
        errors.append(f"ZERO_VOLUME_PCT={zero_pct:.2f}")

    print("DATA_QUALITY_REPORT")
    print(f"symbol={args.symbol}")
    print(f"timeframe={args.timeframe}")
    print(f"bars={bars_count}")
    print(f"ticks={ticks_count}")
    print(f"period={min_ts}..{max_ts}")
    print(f"duplicates={duplicates}")
    print(f"gaps>{args.max_gap_min}min={gaps}")
    print(f"zero_volume={zero_volume} ({zero_pct:.2f}%)")
    print(f"bad_prices={bad_prices}")

    if errors:
        print("STATUS=FAIL")
        print("ERRORS=" + ",".join(errors))
        return 1

    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
