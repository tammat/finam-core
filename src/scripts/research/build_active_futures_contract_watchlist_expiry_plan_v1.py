#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import psycopg


NOW_UTC = datetime.now(timezone.utc)
FRESH_MINUTES = int(os.getenv("FRESH_MINUTES", "240"))
STALE_DAYS = int(os.getenv("STALE_DAYS", "7"))

FUTURES_PREFIXES = tuple(
    x.strip().upper()
    for x in os.getenv("FUTURES_PREFIXES", "BR,NG,GD").split(",")
    if x.strip()
)

MONTH_CODES = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}


def classify_family(symbol: str) -> str:
    s = symbol.upper()
    if s.startswith("BR"):
        return "BRENT_FUTURES"
    if s.startswith("NG"):
        return "GAS_FUTURES"
    if s.startswith("GD"):
        return "GOLD_FUTURES"
    return "UNKNOWN_FUTURES"


def parse_contract_month(symbol: str) -> tuple[int | None, int | None, str | None]:
    """Русский комментарий: парсим BRN6/NGM6 по стандартному month-code.

    Возвращаем: year, month, month_code.
    Для 2026 используем последнюю цифру года. Это эвристика для watchlist, не биржевой календарь.
    """
    base = symbol.split("@", 1)[0].upper()
    match = re.match(r"^[A-Z]+([FGHJKMNQUVXZ])([0-9])$", base)
    if not match:
        return None, None, None

    month_code = match.group(1)
    year_digit = int(match.group(2))

    year = 2020 + year_digit
    if year < NOW_UTC.year - 1:
        year += 10

    return year, MONTH_CODES.get(month_code), month_code


def expiry_bucket(symbol: str, last_ts) -> str:
    year, month, _ = parse_contract_month(symbol)

    if year is None or month is None:
        return "EXPIRY_UNKNOWN"

    # Русский комментарий: грубая календарная оценка. Для точной экспирации позже нужен биржевой календарь.
    if year < NOW_UTC.year or (year == NOW_UTC.year and month < NOW_UTC.month):
        return "EXPIRED_BY_CONTRACT_CODE"

    if year == NOW_UTC.year and month == NOW_UTC.month:
        return "FRONT_OR_EXPIRING_MONTH"

    if year == NOW_UTC.year and month == NOW_UTC.month + 1:
        return "NEXT_MONTH"

    return "FAR_MONTH"


def freshness_bucket(last_ts) -> str:
    if last_ts is None:
        return "NO_BARS"

    delta = NOW_UTC - last_ts.astimezone(timezone.utc)
    minutes = delta.total_seconds() / 60.0

    if minutes <= FRESH_MINUTES:
        return "FRESH"
    if minutes <= STALE_DAYS * 24 * 60:
        return "STALE_INTRAWEEK"
    return "STALE_OR_DEAD"


def main() -> int:
    print("=== ACTIVE FUTURES CONTRACT WATCHLIST EXPIRY PLAN V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"now_utc={NOW_UTC.isoformat()}")
    print(f"fresh_minutes={FRESH_MINUTES}")
    print(f"stale_days={STALE_DAYS}")
    print(f"futures_prefixes={','.join(FUTURES_PREFIXES)}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            where_parts = []
            params = []

            for prefix in FUTURES_PREFIXES:
                where_parts.append("symbol like %s")
                params.append(f"{prefix}%@RTSX")

            sql = f"""
                select
                    symbol,
                    timeframe,
                    count(*)::int as bars,
                    min(ts) as first_ts,
                    max(ts) as last_ts,
                    max(volume) as max_volume,
                    avg(volume) as avg_volume
                from market_bars
                where ({' or '.join(where_parts)})
                  and timeframe in ('M1', 'M5', 'M15')
                group by symbol, timeframe
                order by symbol, timeframe
            """

            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            print()
            print("ACTIVE_FUTURES_CONTRACT_ROWS")

            total = 0
            fresh = 0
            expired = 0
            stale_or_dead = 0
            watch_candidates = 0

            for symbol, timeframe, bars, first_ts, last_ts, max_volume, avg_volume in rows:
                total += 1

                family = classify_family(symbol)
                year, month, month_code = parse_contract_month(symbol)
                fresh_bucket = freshness_bucket(last_ts)
                exp_bucket = expiry_bucket(symbol, last_ts)

                if fresh_bucket == "FRESH":
                    fresh += 1
                if exp_bucket == "EXPIRED_BY_CONTRACT_CODE":
                    expired += 1
                if fresh_bucket == "STALE_OR_DEAD":
                    stale_or_dead += 1

                is_candidate = (
                    fresh_bucket == "FRESH"
                    and exp_bucket in {"FRONT_OR_EXPIRING_MONTH", "NEXT_MONTH", "FAR_MONTH", "EXPIRY_UNKNOWN"}
                    and int(bars or 0) >= 30
                )

                watch_candidates += int(is_candidate)

                print(
                    "ACTIVE_FUTURES_CONTRACT_ROW "
                    f"symbol={symbol} family={family} timeframe={timeframe} "
                    f"bars={bars} first_ts={first_ts} last_ts={last_ts} "
                    f"contract_year={year} contract_month={month} month_code={month_code} "
                    f"freshness={fresh_bucket} expiry_bucket={exp_bucket} "
                    f"max_volume={float(max_volume or 0):.2f} avg_volume={float(avg_volume or 0):.2f} "
                    f"watch_candidate={int(is_candidate)}"
                )

    print()
    print("ACTIVE_FUTURES_CONTRACT_WATCHLIST_EXPIRY_PLAN_SUMMARY")
    print(f"rows_total={total}")
    print(f"fresh_rows={fresh}")
    print(f"expired_rows={expired}")
    print(f"stale_or_dead_rows={stale_or_dead}")
    print(f"watch_candidates={watch_candidates}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if watch_candidates > 0:
        print("VERDICT=ACTIVE_FUTURES_CONTRACT_WATCHLIST_CANDIDATES_FOUND")
    elif total > 0:
        print("VERDICT=ACTIVE_FUTURES_CONTRACT_WATCHLIST_NO_FRESH_CANDIDATES")
    else:
        print("VERDICT=ACTIVE_FUTURES_CONTRACT_WATCHLIST_NO_CONTRACT_ROWS")

    print("ACTIVE_FUTURES_CONTRACT_WATCHLIST_EXPIRY_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
