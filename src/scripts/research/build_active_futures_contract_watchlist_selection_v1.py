#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import datetime, timezone

import psycopg


NOW_UTC = datetime.now(timezone.utc)
FRESH_MINUTES = int(os.getenv("FRESH_MINUTES", "240"))
MIN_BARS = int(os.getenv("MIN_BARS", "30"))
FUTURES_PREFIXES = tuple(
    x.strip().upper()
    for x in os.getenv("FUTURES_PREFIXES", "BR,NG,GD").split(",")
    if x.strip()
)

MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}


def family(symbol: str) -> str:
    s = symbol.upper()
    if s.startswith("BR"):
        return "BRENT_FUTURES"
    if s.startswith("NG"):
        return "GAS_FUTURES"
    if s.startswith("GD"):
        return "GOLD_FUTURES"
    return "UNKNOWN_FUTURES"


def parse_month(symbol: str) -> tuple[int | None, int | None, str | None]:
    base = symbol.split("@", 1)[0].upper()
    match = re.match(r"^[A-Z]+([FGHJKMNQUVXZ])([0-9])$", base)
    if not match:
        return None, None, None

    code = match.group(1)
    digit = int(match.group(2))
    year = 2020 + digit
    if year < NOW_UTC.year - 1:
        year += 10

    return year, MONTH_CODES.get(code), code


def freshness(last_ts) -> str:
    if last_ts is None:
        return "NO_BARS"
    minutes = (NOW_UTC - last_ts.astimezone(timezone.utc)).total_seconds() / 60.0
    if minutes <= FRESH_MINUTES:
        return "FRESH"
    return "STALE"


def expiry_bucket(symbol: str) -> str:
    year, month, _ = parse_month(symbol)
    if year is None or month is None:
        return "EXPIRY_UNKNOWN"
    if year < NOW_UTC.year or (year == NOW_UTC.year and month < NOW_UTC.month):
        return "EXPIRED"
    if year == NOW_UTC.year and month == NOW_UTC.month:
        return "FRONT"
    if year == NOW_UTC.year and month == NOW_UTC.month + 1:
        return "NEXT"
    return "FAR"


def main() -> int:
    print("=== ACTIVE FUTURES CONTRACT WATCHLIST SELECTION V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"now_utc={NOW_UTC.isoformat()}")
    print(f"futures_prefixes={','.join(FUTURES_PREFIXES)}")
    print(f"fresh_minutes={FRESH_MINUTES}")
    print(f"min_bars={MIN_BARS}")

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

            cur.execute(
                f"""
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
                  and timeframe in ('M1', 'M5')
                group by symbol, timeframe
                order by symbol, timeframe
                """,
                tuple(params),
            )
            raw_rows = cur.fetchall()

    candidates = []
    for symbol, timeframe, bars, first_ts, last_ts, max_volume, avg_volume in raw_rows:
        fam = family(symbol)
        exp = expiry_bucket(symbol)
        fresh = freshness(last_ts)
        year, month, code = parse_month(symbol)

        is_candidate = (
            fam != "UNKNOWN_FUTURES"
            and fresh == "FRESH"
            and exp in {"FRONT", "NEXT", "FAR", "EXPIRY_UNKNOWN"}
            and int(bars or 0) >= MIN_BARS
        )

        liquidity_score = float(avg_volume or 0.0)
        if timeframe == "M5":
            liquidity_score *= 1.15

        candidates.append(
            {
                "symbol": symbol,
                "family": fam,
                "timeframe": timeframe,
                "bars": int(bars or 0),
                "first_ts": first_ts,
                "last_ts": last_ts,
                "max_volume": float(max_volume or 0.0),
                "avg_volume": float(avg_volume or 0.0),
                "freshness": fresh,
                "expiry_bucket": exp,
                "contract_year": year,
                "contract_month": month,
                "month_code": code,
                "watch_candidate": is_candidate,
                "liquidity_score": liquidity_score,
            }
        )

    print()
    print("ACTIVE_FUTURES_CONTRACT_SELECTION_INPUT_ROWS")
    for row in candidates:
        print(
            "ACTIVE_FUTURES_CONTRACT_SELECTION_INPUT_ROW "
            f"symbol={row['symbol']} family={row['family']} timeframe={row['timeframe']} "
            f"bars={row['bars']} last_ts={row['last_ts']} freshness={row['freshness']} "
            f"expiry_bucket={row['expiry_bucket']} avg_volume={row['avg_volume']:.2f} "
            f"max_volume={row['max_volume']:.2f} liquidity_score={row['liquidity_score']:.2f} "
            f"watch_candidate={int(row['watch_candidate'])}"
        )

    grouped = defaultdict(list)
    for row in candidates:
        if row["watch_candidate"]:
            grouped[row["family"]].append(row)

    print()
    print("ACTIVE_FUTURES_CONTRACT_SELECTION_ROWS")

    selected_total = 0
    primary_total = 0
    secondary_total = 0
    research_total = 0

    for fam, rows in sorted(grouped.items()):
        rows_sorted = sorted(
            rows,
            key=lambda r: (
                {"FRONT": 0, "NEXT": 1, "FAR": 2, "EXPIRY_UNKNOWN": 3}.get(r["expiry_bucket"], 9),
                -r["liquidity_score"],
            ),
        )

        selected_for_family = []

        # Берём самый ликвидный FRONT/NEXT как PRIMARY, затем один NEXT/FAR как SECONDARY,
        # остальное свежие дальние — research/watch only.
        primary = None
        for row in rows_sorted:
            if row["expiry_bucket"] in {"FRONT", "NEXT"}:
                primary = row
                break
        if primary is None and rows_sorted:
            primary = rows_sorted[0]

        if primary:
            selected_for_family.append((primary, "PRIMARY_WATCH"))

            primary_base = str(primary["symbol"]).split("@", 1)[0]
            for row in rows_sorted:
                row_base = str(row["symbol"]).split("@", 1)[0]
                if row is primary:
                    continue
                if row_base == primary_base and row["timeframe"] == "M1":
                    selected_for_family.append((row, "INTRADAY_WATCH"))
                    break

        for row in rows_sorted:
            if row is primary:
                continue
            if any(row is selected for selected, _role in selected_for_family):
                continue
            if row["expiry_bucket"] in {"NEXT", "FAR"}:
                selected_for_family.append((row, "SECONDARY_WATCH"))
                break

        for row in rows_sorted:
            if any(row is selected for selected, _role in selected_for_family):
                continue
            selected_for_family.append((row, "RESEARCH_WATCH"))

        for row, role in selected_for_family:
            selected_total += 1
            primary_total += int(role == "PRIMARY_WATCH")
            secondary_total += int(role == "SECONDARY_WATCH")
            research_total += int(role == "RESEARCH_WATCH")

            print(
                "ACTIVE_FUTURES_CONTRACT_SELECTION_ROW "
                f"family={fam} symbol={row['symbol']} timeframe={row['timeframe']} "
                f"role={role} expiry_bucket={row['expiry_bucket']} freshness={row['freshness']} "
                f"bars={row['bars']} avg_volume={row['avg_volume']:.2f} "
                f"liquidity_score={row['liquidity_score']:.2f} "
                "db_update=0"
            )

    print()
    print("ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_SUMMARY")
    print(f"families_total={len(grouped)}")
    print(f"input_rows_total={len(candidates)}")
    print(f"candidate_rows_total={sum(1 for r in candidates if r['watch_candidate'])}")
    print(f"selected_total={selected_total}")
    print(f"primary_total={primary_total}")
    print(f"secondary_total={secondary_total}")
    print(f"research_total={research_total}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if selected_total > 0 and primary_total >= len(grouped):
        print("VERDICT=ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_READY")
    elif selected_total > 0:
        print("VERDICT=ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_PARTIAL")
    else:
        print("VERDICT=ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_EMPTY")

    print("ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
