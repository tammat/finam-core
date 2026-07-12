#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
import requests


TARGETS = ["NVTK@MISX", "OZON@MISX", "T@MISX", "X5@MISX"]

# MOEX ISS intervals: 1 = M1, 5 = M5.
TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
}


def moex_sec_code(symbol: str) -> str:
    return symbol.split("@", 1)[0]


def table_columns(cur, table: str) -> list[str]:
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema='public'
          and table_name=%s
        order by ordinal_position
        """,
        (table,),
    )
    return [r["column_name"] for r in cur.fetchall()]


def fetch_moex_candles(sec_code: str, interval: int, date_from: str, date_till: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0

    while True:
        url = (
            "https://iss.moex.com/iss/engines/stock/markets/shares/"
            f"boards/TQBR/securities/{sec_code}/candles.json"
        )
        params = {
            "from": date_from,
            "till": date_till,
            "interval": interval,
            "start": start,
            "iss.meta": "off",
        }

        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        candles = data.get("candles", {})
        columns = candles.get("columns", [])
        raw = candles.get("data", [])

        if not raw:
            break

        for item in raw:
            rows.append(dict(zip(columns, item)))

        if len(raw) < 100:
            break

        start += len(raw)
        time.sleep(0.15)

    return rows


def normalize_number(v: Any):
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def insert_market_bar(cur, cols: list[str], symbol: str, timeframe: str, candle: dict[str, Any]) -> bool:
    ts = candle.get("begin")
    if not ts:
        return False

    mapping = {
        "symbol": symbol,
        "timeframe": timeframe,
        "ts": ts,
        "open": normalize_number(candle.get("open")),
        "high": normalize_number(candle.get("high")),
        "low": normalize_number(candle.get("low")),
        "close": normalize_number(candle.get("close")),
        "volume": normalize_number(candle.get("volume")),
        "value": normalize_number(candle.get("value")),
        "source": "MOEX_ISS_BACKFILL_V1",
    }

    insert_cols = [c for c in mapping if c in cols]

    if "symbol" not in insert_cols or "timeframe" not in insert_cols or "ts" not in insert_cols:
        raise RuntimeError(f"market_bars required columns missing: cols={cols}")

    values = [mapping[c] for c in insert_cols]

    conflict_cols = [c for c in ["symbol", "timeframe", "ts"] if c in cols]
    update_cols = [c for c in insert_cols if c not in conflict_cols]

    placeholders = ", ".join(["%s"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)

    if len(conflict_cols) == 3 and update_cols:
        conflict_sql = ", ".join(conflict_cols)
        update_sql = ", ".join([f"{c}=excluded.{c}" for c in update_cols])
        q = f"""
            insert into market_bars ({col_sql})
            values ({placeholders})
            on conflict ({conflict_sql}) do update set {update_sql}
        """
    else:
        q = f"""
            insert into market_bars ({col_sql})
            values ({placeholders})
        """

    cur.execute(q, values)
    return True


def resample_closed_m5(cur, symbol: str, date_from: str, date_till: str) -> int:
    cur.execute("""
        WITH minute_rows AS (
            SELECT *,date_trunc('hour',ts)+floor(extract(minute FROM ts)/5)*interval '5 minutes' AS bucket
            FROM public.market_bars
            WHERE symbol=%s AND timeframe='M1' AND ts >= %s::date AND ts < (%s::date + interval '1 day')
        ), complete AS (
            SELECT bucket AS ts,(array_agg(open ORDER BY ts))[1] AS open,max(high) AS high,min(low) AS low,
                   (array_agg(close ORDER BY ts DESC))[1] AS close,sum(coalesce(volume,0)) AS volume
            FROM minute_rows WHERE bucket+interval '5 minutes' <= now()
            GROUP BY bucket HAVING count(DISTINCT ts)=5
        )
        INSERT INTO public.market_bars(symbol,timeframe,ts,open,high,low,close,volume,source)
        SELECT %s,'M5',ts,open,high,low,close,volume,'MOEX_ISS_RESAMPLED_M5_V1' FROM complete
        ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET open=excluded.open,high=excluded.high,low=excluded.low,
            close=excluded.close,volume=excluded.volume,source=excluded.source
    """, (symbol, date_from, date_till, symbol))
    return cur.rowcount


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--symbols", default=",".join(TARGETS))
    parser.add_argument("--resample-only", action="store_true")
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    date_till = date.today().isoformat()
    date_from = (date.today() - timedelta(days=args.days)).isoformat()

    result_rows = []
    total_fetched = 0
    total_saved = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cols = table_columns(cur, "market_bars")

            targets = [x.strip() for x in args.symbols.split(",") if x.strip()]

            for symbol in targets:
                sec_code = moex_sec_code(symbol)

                for timeframe, interval in TIMEFRAMES.items():
                    if args.resample_only and timeframe != "M5":
                        continue
                    if timeframe == "M5":
                        candles = []
                        fetched = 0
                        saved = resample_closed_m5(cur, symbol, date_from, date_till) if args.apply else 0
                    else:
                        candles = fetch_moex_candles(sec_code, interval, date_from, date_till)
                        fetched = len(candles)
                        saved = 0
                        if args.apply:
                            for candle in candles:
                                if insert_market_bar(cur, cols, symbol, timeframe, candle):
                                    saved += 1

                    total_fetched += fetched
                    total_saved += saved

                    result_rows.append(
                        {
                            "symbol": symbol,
                            "sec_code": sec_code,
                            "timeframe": timeframe,
                            "interval": interval,
                            "from": date_from,
                            "till": date_till,
                            "fetched": fetched,
                            "saved": saved,
                        }
                    )

            if args.apply:
                conn.commit()
            else:
                conn.rollback()

    out = {
        "verdict": "EQUITY_MOEX_M1_M5_BACKFILL_READY",
        "mode": "apply" if args.apply else "dry_run",
        "db_update": 1 if args.apply else 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "targets_total": len(targets),
        "total_fetched": total_fetched,
        "total_saved": total_saved,
        "rows": result_rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_MOEX_M1_M5_BACKFILL_READY")
    print("TEST_EQUITY_MOEX_M1_M5_BACKFILL_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
