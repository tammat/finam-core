# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime, timezone

import psycopg2


def dsn() -> str:
    return os.getenv("DATABASE_URL") or (
        f"postgresql://{os.getenv('DB_USER','finam')}:{os.getenv('DB_PASSWORD','finam')}"
        f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','finam')}"
    )


def parse_ts(value: str | None):
    """Русский комментарий: парсинг ISO timestamp для фильтра периода DQ."""
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--timeframe", default="M1")
    p.add_argument("--max-gap-min", type=int, default=3)
    p.add_argument("--max-zero-volume-pct", type=float, default=50.0)
    p.add_argument("--from-ts", default=None, help="Начало проверяемого периода, ISO timestamp")
    p.add_argument("--to-ts", default=None, help="Конец проверяемого периода, ISO timestamp")
    p.add_argument("--allow-zero-volume", action="store_true", help="Не считать нулевой объём критичной ошибкой")
    args = p.parse_args()

    from_ts = parse_ts(args.from_ts)
    to_ts = parse_ts(args.to_ts)

    errors = []

    bar_filter = "symbol=%s AND timeframe=%s"
    bar_params = [args.symbol, args.timeframe]

    tick_filter = "symbol=%s"
    tick_params = [args.symbol]

    if from_ts is not None:
        bar_filter += " AND ts >= %s"
        bar_params.append(from_ts)
        tick_filter += " AND ts >= %s"
        tick_params.append(from_ts)

    if to_ts is not None:
        bar_filter += " AND ts <= %s"
        bar_params.append(to_ts)
        tick_filter += " AND ts <= %s"
        tick_params.append(to_ts)

    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT count(*), min(ts), max(ts)
                FROM market_data
                WHERE {bar_filter}
            """, tuple(bar_params))
            bars_count, min_ts, max_ts = cur.fetchone()

            cur.execute(f"""
                SELECT count(*)
                FROM market_ticks
                WHERE {tick_filter}
            """, tuple(tick_params))
            ticks_count = cur.fetchone()[0]

            cur.execute(f"""
                SELECT count(*)
                FROM market_data
                WHERE {bar_filter} AND volume = 0
            """, tuple(bar_params))
            zero_volume = cur.fetchone()[0]

            cur.execute(f"""
                SELECT count(*)
                FROM (
                    SELECT symbol, timeframe, ts, count(*)
                    FROM market_data
                    WHERE {bar_filter}
                    GROUP BY symbol, timeframe, ts
                    HAVING count(*) > 1
                ) d
            """, tuple(bar_params))
            duplicates = cur.fetchone()[0]

            cur.execute(f"""
                WITH x AS (
                    SELECT
                        ts,
                        lag(ts) OVER (ORDER BY ts) AS prev_ts
                    FROM market_data
                    WHERE {bar_filter}
                )
                SELECT count(*)
                FROM x
                WHERE prev_ts IS NOT NULL
                  AND EXTRACT(EPOCH FROM (ts - prev_ts)) / 60.0 > %s
            """, tuple(bar_params + [args.max_gap_min]))
            gaps = cur.fetchone()[0]

            cur.execute(f"""
                SELECT count(*)
                FROM market_data
                WHERE {bar_filter}
                  AND (
                      close_price <= 0
                      OR high < low
                      OR open IS NULL
                      OR high IS NULL
                      OR low IS NULL
                  )
            """, tuple(bar_params))
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
    if not args.allow_zero_volume and zero_pct > args.max_zero_volume_pct:
        errors.append(f"ZERO_VOLUME_PCT={zero_pct:.2f}")

    print("DATA_QUALITY_REPORT")
    print(f"symbol={args.symbol}")
    print(f"timeframe={args.timeframe}")
    print(f"from_ts={from_ts}")
    print(f"to_ts={to_ts}")
    print(f"allow_zero_volume={args.allow_zero_volume}")
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
