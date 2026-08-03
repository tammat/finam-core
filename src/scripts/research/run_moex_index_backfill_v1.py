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


# IMOEX2 is the extended-hours broad-market regime feed. RVI is intentionally
# collected as a non-tradable volatility-regime feature; it may remain empty
# before the main index session starts.
TARGETS = ["IMOEX", "IMOEX2", "RTSI", "RVI"]
TIMEFRAMES = {"M1": 1, "M5": 5}


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


def fetch_moex_index_candles(sec_code: str, interval: int, date_from: str, date_till: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0

    while True:
        url = (
            "https://iss.moex.com/iss/engines/stock/markets/index/"
            f"securities/{sec_code}/candles.json"
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


def insert_market_bar(cur, cols: list[str], symbol: str, timeframe: str, candle: dict[str, Any], source: str = "MOEX_INDEX_BACKFILL_V1") -> bool:
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
        "volume": normalize_number(candle.get("volume") or 0),
        "source": source,
    }

    insert_cols = [c for c in mapping if c in cols]
    values = [mapping[c] for c in insert_cols]

    required = {"symbol", "timeframe", "ts", "open", "high", "low", "close"}
    if not required.issubset(set(insert_cols)):
        raise RuntimeError(f"market_bars required columns missing: cols={cols}")

    placeholders = ", ".join(["%s"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)

    update_cols = [c for c in insert_cols if c not in {"symbol", "timeframe", "ts"}]
    update_sql = ", ".join([f"{c}=excluded.{c}" for c in update_cols])

    cur.execute(
        f"""
        insert into market_bars ({col_sql})
        values ({placeholders})
        on conflict (symbol, timeframe, ts)
        do update set {update_sql}
        """,
        values,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--symbols", default=",".join(TARGETS))
    args = parser.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    date_till = date.today().isoformat()
    date_from = (date.today() - timedelta(days=args.days)).isoformat()

    result_rows = []
    total_fetched = 0
    total_saved = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cols = table_columns(cur, "market_bars")

            for symbol in symbols:
                for timeframe, interval in TIMEFRAMES.items():
                    candles = fetch_moex_index_candles(symbol, interval, date_from, date_till)
                    fetched = len(candles)
                    saved = 0

                    if args.apply:
                        for candle in candles:
                            if insert_market_bar(cur, cols, symbol, timeframe, candle):
                                saved += 1

                    total_fetched += fetched
                    total_saved += saved

                    result_rows.append({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "interval": interval,
                        "from": date_from,
                        "till": date_till,
                        "fetched": fetched,
                        "saved": saved,
                    })

            if args.apply:
                conn.commit()
            else:
                conn.rollback()

    out = {
        "verdict": "MOEX_INDEX_BACKFILL_READY",
        "mode": "apply" if args.apply else "dry_run",
        "db_update": 1 if args.apply else 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "targets_total": len(symbols),
        "total_fetched": total_fetched,
        "total_saved": total_saved,
        "rows": result_rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("VERDICT=MOEX_INDEX_BACKFILL_READY")
    print("TEST_MOEX_INDEX_BACKFILL_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
