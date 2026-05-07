# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.data.volatility_scanner import VolatilityScanner


def load_rows(database_url: str, timeframe: str, lookback_bars: int, table_name: str) -> list[dict]:
    sql = f"""
    WITH recent AS (
        SELECT
            symbol,
            ts,
            open,
            high,
            low,
            close_price,
            volume,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
        FROM {table_name}
        WHERE timeframe = %s
    )
    SELECT
        symbol,
        MIN(open) FILTER (WHERE rn = %s) AS open,
        MAX(high) AS high,
        MIN(low) AS low,
        (ARRAY_AGG(close_price ORDER BY ts DESC))[1] AS close,
        (ARRAY_AGG(close_price ORDER BY ts DESC))[1] AS last,
        (ARRAY_AGG(volume ORDER BY ts DESC))[1] AS volume,
        AVG(volume) AS avg_volume,
        SUM(close_price * volume) AS turnover,
        0 AS bid,
        0 AS ask
    FROM recent
    WHERE rn <= %s
    GROUP BY symbol
    HAVING COUNT(*) >= LEAST(%s, 20)
    """

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as check_cur:
            check_cur.execute("SELECT to_regclass(%s)", (table_name,))
            if check_cur.fetchone()[0] is None:
                raise SystemExit(
                    f"BARS_TABLE_NOT_FOUND table={table_name}. "
                    "Run psql '$DATABASE_URL' -c '\\dt' and pass --table <name>."
                )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (timeframe, lookback_bars, lookback_bars, lookback_bars))
            return [dict(row) for row in cur.fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback-bars", type=int, default=60)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--min-turnover", type=float, default=300_000_000)
    parser.add_argument("--table", default=os.getenv("BARS_TABLE", "market_data"))
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    rows = load_rows(database_url, args.timeframe, args.lookback_bars, args.table)

    scanner = VolatilityScanner(min_turnover=args.min_turnover)
    result = scanner.scan(rows, top_n=args.top_n)

    print("TOP_INTRADAY")
    for item in result["intraday"]:
        print(item)

    print("\nTOP_SWING")
    for item in result["swing"]:
        print(item)

    print("VOLATILITY_SCAN_REAL_DATA_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
