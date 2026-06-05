#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


EXPECTED = [
    ("BRN6@RTSX", "M1"),
    ("BRN6@RTSX", "M5"),
    ("NGN6@RTSX", "M1"),
    ("NGN6@RTSX", "M5"),
    ("USDRUBF@RTSX", "M1"),
    ("USDRUBF@RTSX", "M5"),
    ("BTCUSD", "M1"),
    ("BTCUSD", "M5"),
    ("ETHUSD", "M1"),
    ("ETHUSD", "M5"),
]


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main() -> None:
    print("=== RESEARCH FEATURE FRESHNESS HEALTH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute("""
                select exists (
                    select 1
                    from information_schema.tables
                    where table_name='research_feature_store'
                );
            """)
            table_exists = bool(cur.fetchone()[0])

            if not table_exists:
                print("TABLE_EXISTS=0")
                print("VERDICT=NO_FEATURE_STORE_TABLE")
                return

            cur.execute("""
                select
                    symbol,
                    timeframe,
                    count(*) as rows,
                    max(ts) as last_ts,
                    round(extract(epoch from (now() - max(ts))) / 60, 2) as lag_min,
                    count(atr_14) as atr_rows,
                    count(ema_20) as ema20_rows,
                    count(momentum_20) as momentum20_rows,
                    sum(case when compression_flag then 1 else 0 end) as compression_rows,
                    sum(case when expansion_flag then 1 else 0 end) as expansion_rows
                from research_feature_store
                group by symbol, timeframe;
            """)
            rows = cur.fetchall()

    actual = {(r[0], r[1]): r for r in rows}

    missing = 0
    stale = 0
    weak = 0
    ok = 0

    for symbol, timeframe in EXPECTED:
        row = actual.get((symbol, timeframe))
        if row is None:
            missing += 1
            print(
                f"FEATURE_HEALTH_ROW symbol={symbol} timeframe={timeframe} "
                f"status=MISSING rows=0 lag_min=None"
            )
            continue

        (
            _symbol,
            _timeframe,
            rows_count,
            last_ts,
            lag_min,
            atr_rows,
            ema20_rows,
            momentum20_rows,
            compression_rows,
            expansion_rows,
        ) = row

        lag = float(lag_min or 0)
        rows_int = int(rows_count or 0)

        if rows_int < 200:
            status = "WEAK_HISTORY"
            weak += 1
        elif lag > 180:
            status = "STALE"
            stale += 1
        else:
            status = "OK"
            ok += 1

        print(
            f"FEATURE_HEALTH_ROW symbol={symbol} timeframe={timeframe} "
            f"status={status} rows={rows_int} last_ts={last_ts} "
            f"lag_min={lag:.2f} atr_rows={atr_rows} ema20_rows={ema20_rows} "
            f"momentum20_rows={momentum20_rows} compression_rows={compression_rows} "
            f"expansion_rows={expansion_rows}"
        )

    print()
    print(f"SUMMARY ok={ok} stale={stale} weak={weak} missing={missing}")

    if missing > 0:
        print("VERDICT=FEATURE_HEALTH_MISSING")
    elif stale > 0:
        print("VERDICT=FEATURE_HEALTH_STALE")
    elif weak > 0:
        print("VERDICT=FEATURE_HEALTH_WEAK_HISTORY")
    else:
        print("VERDICT=OK")


if __name__ == "__main__":
    main()
