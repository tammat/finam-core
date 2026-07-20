from __future__ import annotations

import os

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "M15_FROM_FRESH_M5_V1"


SQL = """
WITH fresh_symbols AS (
    SELECT symbol
    FROM public.market_bars
    WHERE timeframe='M5'
    GROUP BY symbol
    HAVING max(ts) >= clock_timestamp()-interval '30 minutes'
), grouped AS (
    SELECT b.symbol,
           date_bin(interval '15 minutes',b.ts,timestamptz '2000-01-01 00:00:00+00') AS bucket,
           min(b.ts) AS first_ts,max(b.ts) AS last_ts,count(*) AS bars,
           (array_agg(b.open ORDER BY b.ts))[1] AS open,
           max(b.high) AS high,min(b.low) AS low,
           (array_agg(b.close ORDER BY b.ts DESC))[1] AS close,
           sum(coalesce(b.volume,0)) AS volume
    FROM public.market_bars b
    JOIN fresh_symbols f USING(symbol)
    WHERE b.timeframe='M5'
      AND b.ts >= clock_timestamp()-interval '120 days'
      AND b.ts < date_bin(interval '15 minutes',clock_timestamp(),timestamptz '2000-01-01 00:00:00+00')
      AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1')
    GROUP BY b.symbol,date_bin(interval '15 minutes',b.ts,timestamptz '2000-01-01 00:00:00+00')
    HAVING count(*)=3 AND max(b.ts)-min(b.ts)=interval '10 minutes'
), written AS (
    INSERT INTO public.market_bars(symbol,timeframe,ts,open,high,low,close,volume,source)
    SELECT symbol,'M15',bucket,open,high,low,close,volume,%s
    FROM grouped
    ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
      open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
      volume=excluded.volume,source=excluded.source,created_at=clock_timestamp()
    RETURNING symbol,ts
)
SELECT count(*) AS rows_written,count(DISTINCT symbol) AS symbols FROM written
"""


def main() -> int:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_xact_lock(%s)",(941903162,))
            if not cur.fetchone()[0]:
                print("VERDICT=M15_REBUILD_ALREADY_RUNNING")
                return 0
            cur.execute(SQL,(SOURCE_VERSION,))
            rows_written,symbols=cur.fetchone()
    print(f"rows_written={rows_written}")
    print(f"symbols={symbols}")
    print("VERDICT=M15_REBUILT_FROM_FRESH_M5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
