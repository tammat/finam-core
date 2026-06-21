#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row


FUTURES_WHERE = """
(
    symbol like 'NG%@RTSX'
    or symbol like 'BR%@RTSX'
    or symbol like 'GD%@RTSX'
    or symbol like 'GL%@RTSX'
    or symbol like 'SV%@RTSX'
    or symbol = 'USDRUBF@RTSX'
)
"""

FRESH_DAYS_LIMIT = 14
MIN_BARS_M1 = 100
MIN_BARS_M5 = 50


def family(symbol: str) -> str:
    for p in ("USDRUBF", "NG", "BR", "GD", "GL", "SV"):
        if symbol.startswith(p):
            return p
    return "OTHER"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    rows_out = []

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                select
                    symbol,
                    timeframe,
                    count(*)::int as bars,
                    min(ts) as first_ts,
                    max(ts) as last_ts,
                    count(*) filter (where close is null)::int as close_nulls,
                    count(*) filter (where close <= 0)::int as close_non_positive,
                    count(*) filter (where volume is null)::int as volume_nulls,
                    count(*) filter (where volume = 0)::int as volume_zero,
                    avg(volume) filter (where volume is not null) as avg_volume
                from market_bars
                where timeframe in ('M1','M5')
                  and {FUTURES_WHERE}
                group by symbol, timeframe
                order by symbol, timeframe
            """)
            rows = list(cur.fetchall())

            for r in rows:
                now = datetime.now(timezone.utc)
                last_ts = r["last_ts"]
                age_days = None
                if last_ts is not None:
                    age_days = (now - last_ts).total_seconds() / 86400

                min_bars = MIN_BARS_M1 if r["timeframe"] == "M1" else MIN_BARS_M5

                stale = age_days is None or age_days > FRESH_DAYS_LIMIT
                insufficient = r["bars"] < min_bars
                bad_close = r["close_nulls"] > 0 or r["close_non_positive"] > 0
                weak_volume = r["volume_nulls"] == r["bars"] or r["volume_zero"] == r["bars"]

                quality = "OK"
                reasons = []

                if stale:
                    quality = "EXCLUDE"
                    reasons.append("STALE")
                if insufficient:
                    quality = "EXCLUDE"
                    reasons.append("INSUFFICIENT_BARS")
                if bad_close:
                    quality = "EXCLUDE"
                    reasons.append("BAD_CLOSE")
                if weak_volume:
                    if quality != "EXCLUDE":
                        quality = "WARN"
                    reasons.append("WEAK_VOLUME")

                rows_out.append({
                    "symbol": r["symbol"],
                    "family": family(r["symbol"]),
                    "timeframe": r["timeframe"],
                    "bars": r["bars"],
                    "first_ts": r["first_ts"],
                    "last_ts": r["last_ts"],
                    "age_days": round(age_days, 2) if age_days is not None else None,
                    "close_nulls": r["close_nulls"],
                    "close_non_positive": r["close_non_positive"],
                    "volume_nulls": r["volume_nulls"],
                    "volume_zero": r["volume_zero"],
                    "avg_volume": r["avg_volume"],
                    "quality": quality,
                    "reasons": ",".join(reasons) if reasons else "NONE",
                })

    total = len(rows_out)
    ok = sum(1 for r in rows_out if r["quality"] == "OK")
    warn = sum(1 for r in rows_out if r["quality"] == "WARN")
    exclude = sum(1 for r in rows_out if r["quality"] == "EXCLUDE")

    print("=== FUTURES_DATA_QUALITY_AUDIT_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print(f"rows_total={total}")
    print(f"quality_ok={ok}")
    print(f"quality_warn={warn}")
    print(f"quality_exclude={exclude}")

    for r in rows_out:
        print(
            "FUTURES_DQ_ROW "
            f"symbol={r['symbol']} "
            f"family={r['family']} "
            f"timeframe={r['timeframe']} "
            f"bars={r['bars']} "
            f"last_ts={r['last_ts']} "
            f"age_days={r['age_days']} "
            f"avg_volume={r['avg_volume']} "
            f"quality={r['quality']} "
            f"reasons={r['reasons']}",
            flush=True,
        )

    verdict = "FUTURES_DATA_QUALITY_AUDIT_READY"
    if ok == 0:
        verdict = "FUTURES_DATA_QUALITY_AUDIT_NO_OK_CONTRACTS"

    print(f"VERDICT={verdict}")
    print("TEST_FUTURES_DATA_QUALITY_AUDIT_V1_OK")

    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
