#!/usr/bin/env python3
import argparse
import os
from datetime import datetime, timezone

import psycopg


EXPECTED_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "H1": 60,
}


def split_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframes", default="M1,M5")
    parser.add_argument("--max-freshness-min", type=float, default=15.0)
    parser.add_argument("--session-gap-min", type=float, default=180.0)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    symbols = split_csv(args.symbols)
    timeframes = split_csv(args.timeframes)

    sql = """
    with ordered as (
        select
            symbol,
            timeframe,
            ts,
            lag(ts) over (
                partition by symbol, timeframe
                order by ts
            ) as prev_ts
        from market_bars
        where symbol = any(%(symbols)s)
          and timeframe = any(%(timeframes)s)
    ),
    gaps as (
        select
            symbol,
            timeframe,
            count(*) filter (
                where prev_ts is not null
                  and extract(epoch from (ts - prev_ts)) / 60.0 > %(gap_multiplier)s * %(expected_minutes)s
                  and extract(epoch from (ts - prev_ts)) / 60.0 < %(session_gap_min)s
            ) as gaps,
            count(*) filter (
                where prev_ts is not null
                  and extract(epoch from (ts - prev_ts)) / 60.0 >= %(session_gap_min)s
            ) as session_closed,
            coalesce(max(extract(epoch from (ts - prev_ts)) / 60.0), 0) as largest_gap_minutes
        from ordered
        group by symbol, timeframe
    ),
    coverage as (
        select
            symbol,
            timeframe,
            count(*) as bars,
            min(ts) as min_ts,
            max(ts) as max_ts
        from market_bars
        where symbol = any(%(symbols)s)
          and timeframe = any(%(timeframes)s)
        group by symbol, timeframe
    )
    select
        c.symbol,
        c.timeframe,
        c.bars,
        c.min_ts,
        c.max_ts,
        coalesce(g.gaps, 0) as gaps,
        coalesce(g.session_closed, 0) as session_closed,
        coalesce(g.largest_gap_minutes, 0) as largest_gap_minutes
    from coverage c
    left join gaps g
      on g.symbol = c.symbol
     and g.timeframe = c.timeframe
    order by c.symbol, c.timeframe;
    """

    now = datetime.now(timezone.utc)

    print(
        "MARKET_BARS_HEALTH_REPORT",
        f"symbols={','.join(symbols)}",
        f"timeframes={','.join(timeframes)}",
        flush=True,
    )

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            for tf in timeframes:
                expected = EXPECTED_MINUTES.get(tf, 5)
                cur.execute(
                    sql,
                    {
                        "symbols": symbols,
                        "timeframes": [tf],
                        "expected_minutes": expected,
                        "gap_multiplier": 3.0,
                        "session_gap_min": args.session_gap_min,
                    },
                )

                for row in cur.fetchall():
                    max_ts = row["max_ts"]
                    freshness_min = (now - max_ts).total_seconds() / 60.0 if max_ts else 999999.0

                    status = "OK"
                    if row["bars"] <= 0:
                        status = "NO_DATA"
                    elif freshness_min > args.max_freshness_min:
                        status = "STALE"
                    elif int(row["gaps"]) > 0:
                        status = "GAPS"

                    print(
                        "MARKET_BARS_HEALTH",
                        f"status={status}",
                        f"symbol={row['symbol']}",
                        f"timeframe={row['timeframe']}",
                        f"bars={row['bars']}",
                        f"min_ts={row['min_ts']}",
                        f"max_ts={row['max_ts']}",
                        f"freshness_min={freshness_min:.1f}",
                        f"intraday_gaps={row['gaps']}",
                        f"session_closed={row['session_closed']}",
                        f"largest_gap_minutes={float(row['largest_gap_minutes']):.1f}",
                        flush=True,
                    )


if __name__ == "__main__":
    main()
