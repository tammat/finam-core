from __future__ import annotations

import argparse
import os
from datetime import date

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True)
    p.add_argument("--timeframes", default="M5")
    p.add_argument("--from-date", required=True)
    p.add_argument("--to-date", required=True)
    args = p.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    timeframes = [x.strip() for x in args.timeframes.split(",") if x.strip()]
    d1 = date.fromisoformat(args.from_date)
    d2 = date.fromisoformat(args.to_date)

    sql = """
    SELECT symbol, timeframe, count(*) AS bars, min(ts) AS first_ts, max(ts) AS last_ts
    FROM market_bars
    WHERE symbol = ANY(%s) AND timeframe = ANY(%s)
    GROUP BY symbol, timeframe
    """

    rows = {}
    with psycopg.connect(os.getenv("DATABASE_URL") or build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (symbols, timeframes))
            for r in cur.fetchall():
                rows[(r["symbol"], r["timeframe"])] = r

    print("HISTORICAL_BACKFILL_PLAN_V1")
    for symbol in symbols:
        for tf in timeframes:
            r = rows.get((symbol, tf))
            if not r:
                print(f"BACKFILL_NEEDED symbol={symbol} timeframe={tf} from={d1} to={d2} reason=no_bars")
                continue

            first_date = r["first_ts"].date()
            last_date = r["last_ts"].date()

            if first_date > d1:
                print(f"BACKFILL_NEEDED symbol={symbol} timeframe={tf} from={d1} to={first_date} reason=history_starts_late bars={r['bars']}")

            if last_date < d2:
                print(f"BACKFILL_NEEDED symbol={symbol} timeframe={tf} from={last_date} to={d2} reason=history_ends_early bars={r['bars']}")

            if first_date <= d1 and last_date >= d2:
                print(f"COVERAGE_OK symbol={symbol} timeframe={tf} bars={r['bars']} first={r['first_ts']} last={r['last_ts']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
