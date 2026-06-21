#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


FRESH_DAYS_LIMIT = Decimal("14")
MIN_BARS = {"M1": 100, "M5": 50}

# Русский комментарий: лимиты ликвидности мягкие; основной отсев делаем по свежести и наличию истории.
MIN_AVG_VOLUME = {
    "BR": Decimal("5"),
    "NG": Decimal("2"),
    "GD": Decimal("5"),
    "GL": Decimal("5"),
    "SV": Decimal("5"),
    "USDRUBF": Decimal("20"),
}

FAMILY_PREFIXES = ("USDRUBF", "NG", "BR", "GD", "GL", "SV")


def family(symbol: str) -> str:
    for p in FAMILY_PREFIXES:
        if symbol.startswith(p):
            return p
    return "OTHER"


def month_code_rank(symbol: str) -> int:
    # Русский комментарий: эвристика сортировки контрактов внутри семейства по буквенным кодам месяцев.
    month_order = {
        "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
        "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
    }

    base = symbol.split("@", 1)[0]

    if base == "USDRUBF":
        return 0

    for prefix in ("NG", "BR", "GD", "GL", "SV"):
        if base.startswith(prefix) and len(base) >= len(prefix) + 2:
            code = base[len(prefix)]
            year = base[len(prefix) + 1:]
            try:
                year_num = int(year)
            except Exception:
                year_num = 0
            return year_num * 100 + month_order.get(code, 99)

    return 999999


def quality_for_row(row: dict) -> tuple[str, list[str], Decimal | None]:
    now = datetime.now(timezone.utc)
    last_ts = row["last_ts"]

    age_days = None
    if last_ts is not None:
        age_days = Decimal(str((now - last_ts).total_seconds() / 86400))

    fam = family(row["symbol"])
    tf = row["timeframe"]
    min_bars = MIN_BARS.get(tf, 50)
    min_volume = MIN_AVG_VOLUME.get(fam, Decimal("1"))

    reasons = []

    if age_days is None or age_days > FRESH_DAYS_LIMIT:
        reasons.append("STALE")
    if row["bars"] < min_bars:
        reasons.append("INSUFFICIENT_BARS")
    if row["close_nulls"] > 0 or row["close_non_positive"] > 0:
        reasons.append("BAD_CLOSE")

    avg_volume = row["avg_volume"]
    if avg_volume is None or Decimal(str(avg_volume)) < min_volume:
        reasons.append("LOW_VOLUME")

    quality = "OK" if not reasons else "EXCLUDE"
    return quality, reasons, age_days


def role_for_contract(index_in_family: int, timeframe: str) -> str:
    if index_in_family == 0 and timeframe == "M5":
        return "PRIMARY_WATCH"
    if index_in_family == 0 and timeframe == "M1":
        return "INTRADAY_WATCH"
    if index_in_family in {1, 2} and timeframe == "M5":
        return "SECONDARY_WATCH"
    if index_in_family == 1 and timeframe == "M1":
        return "INTRADAY_SECONDARY_WATCH"
    return "EXTRA_WATCH"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    raw_rows = []

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    symbol,
                    timeframe,
                    count(*)::int as bars,
                    min(ts) as first_ts,
                    max(ts) as last_ts,
                    count(*) filter (where close is null)::int as close_nulls,
                    count(*) filter (where close <= 0)::int as close_non_positive,
                    avg(volume) filter (where volume is not null) as avg_volume
                from market_bars
                where timeframe in ('M1','M5')
                  and (
                    symbol like 'NG%@RTSX'
                    or symbol like 'BR%@RTSX'
                    or symbol like 'GD%@RTSX'
                    or symbol like 'GL%@RTSX'
                    or symbol like 'SV%@RTSX'
                    or symbol = 'USDRUBF@RTSX'
                  )
                group by symbol, timeframe
                order by symbol, timeframe
            """)
            for row in cur.fetchall():
                quality, reasons, age_days = quality_for_row(row)
                raw_rows.append({
                    "symbol": row["symbol"],
                    "family": family(row["symbol"]),
                    "timeframe": row["timeframe"],
                    "bars": row["bars"],
                    "first_ts": row["first_ts"],
                    "last_ts": row["last_ts"],
                    "age_days": float(age_days) if age_days is not None else None,
                    "avg_volume": row["avg_volume"],
                    "quality": quality,
                    "reasons": reasons,
                    "month_rank": month_code_rank(row["symbol"]),
                })

    ok_rows = [r for r in raw_rows if r["quality"] == "OK"]

    # Русский комментарий: контракт должен иметь M5; M1 без M5 не допускаем в торговую вселенную.
    symbols_with_m5 = {r["symbol"] for r in ok_rows if r["timeframe"] == "M5"}
    ok_rows = [r for r in ok_rows if r["symbol"] in symbols_with_m5]

    by_family_symbols: dict[str, list[str]] = defaultdict(list)
    for sym in sorted(symbols_with_m5, key=month_code_rank):
        fam = family(sym)
        by_family_symbols[fam].append(sym)

    selected_rows = []
    for r in ok_rows:
        fam_symbols = by_family_symbols[r["family"]]
        idx = fam_symbols.index(r["symbol"])
        role = role_for_contract(idx, r["timeframe"])

        # Русский комментарий: для торговли оставляем максимум три контракта на семейство, кроме USDRUBF.
        if r["family"] != "USDRUBF" and idx > 2:
            continue

        if role == "EXTRA_WATCH":
            continue

        selected_rows.append({
            "symbol": r["symbol"],
            "family": r["family"],
            "timeframe": r["timeframe"],
            "role": role,
            "bars": r["bars"],
            "last_ts": r["last_ts"],
            "age_days": r["age_days"],
            "avg_volume": r["avg_volume"],
            "quality": r["quality"],
            "reasons": "NONE",
        })

    selected_rows.sort(key=lambda r: (r["family"], month_code_rank(r["symbol"]), r["timeframe"]))

    out = {
        "verdict": "ACTIVE_FUTURES_UNIVERSE_READY",
        "mode": "read_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "raw_rows": len(raw_rows),
        "quality_ok_rows": len([r for r in raw_rows if r["quality"] == "OK"]),
        "selected_rows": len(selected_rows),
        "selected_symbols": sorted({r["symbol"] for r in selected_rows}, key=month_code_rank),
        "rows": selected_rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    for r in selected_rows:
        print(
            "ACTIVE_FUTURES_ROW "
            f"symbol={r['symbol']} "
            f"family={r['family']} "
            f"timeframe={r['timeframe']} "
            f"role={r['role']} "
            f"bars={r['bars']} "
            f"last_ts={r['last_ts']} "
            f"age_days={r['age_days']} "
            f"avg_volume={r['avg_volume']} "
            f"quality={r['quality']}",
            flush=True,
        )

    print("VERDICT=ACTIVE_FUTURES_UNIVERSE_READY")
    print("TEST_ACTIVE_FUTURES_UNIVERSE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
