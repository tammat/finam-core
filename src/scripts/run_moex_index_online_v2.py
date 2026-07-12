from __future__ import annotations

import json
import os
import argparse
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from scripts.research.run_moex_index_backfill_v1 import TARGETS, fetch_moex_index_candles, insert_market_bar, table_columns


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MOEX_INDEX_ONLINE_V2"
MOSCOW = ZoneInfo("Europe/Moscow")


def closed_candle(candle: dict[str, Any], now: datetime) -> bool:
    end = candle.get("end")
    if not end:
        return False
    return datetime.fromisoformat(str(end)).replace(tzinfo=MOSCOW) <= now


def resample_closed_m5(cur, symbol: str, date_from: str, now: datetime) -> int:
    cur.execute("""
        WITH minute_rows AS (
            SELECT *, date_trunc('hour',ts) + floor(extract(minute FROM ts) / 5) * interval '5 minutes' AS bucket
            FROM public.market_bars
            WHERE symbol=%s AND timeframe='M1' AND ts >= %s::date
        ), complete AS (
            SELECT bucket AS ts,
                   (array_agg(open ORDER BY ts))[1] AS open,
                   max(high) AS high,min(low) AS low,
                   (array_agg(close ORDER BY ts DESC))[1] AS close,
                   sum(coalesce(volume,0)) AS volume
            FROM minute_rows
            WHERE bucket + interval '5 minutes' <= %s
            GROUP BY bucket HAVING count(DISTINCT ts)=5
        )
        INSERT INTO public.market_bars(symbol,timeframe,ts,open,high,low,close,volume,source)
        SELECT %s,'M5',ts,open,high,low,close,volume,%s FROM complete
        ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
            open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
            volume=excluded.volume,source=excluded.source
    """, (symbol, date_from, now, symbol, SOURCE_VERSION))
    return cur.rowcount


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=0, help="Force historical M1 fetch and M5 rebuild for N calendar days")
    args = parser.parse_args()
    now = datetime.now(MOSCOW)
    result: list[dict[str, Any]] = []
    total_saved = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT pg_try_advisory_xact_lock(hashtext(%s)) AS acquired", (SOURCE_VERSION,))
            if not cur.fetchone()["acquired"]:
                print("status=SKIPPED_ALREADY_RUNNING")
                return
            columns = table_columns(cur, "market_bars")
            for symbol in TARGETS:
                cur.execute("SELECT max(ts) AS latest FROM public.market_bars WHERE symbol=%s AND timeframe='M1'", (symbol,))
                previous = cur.fetchone()["latest"]
                if args.days > 0:
                    date_from = (now.date() - timedelta(days=args.days)).isoformat()
                else:
                    date_from = ((previous or now - timedelta(days=30)).date() - timedelta(days=1)).isoformat()
                candles = fetch_moex_index_candles(symbol, 1, date_from, now.date().isoformat())
                complete = [candle for candle in candles if closed_candle(candle, now)]
                m1_saved = sum(insert_market_bar(cur, columns, symbol, "M1", candle, SOURCE_VERSION) for candle in complete)
                m5_saved = resample_closed_m5(cur, symbol, date_from, now)
                total_saved += m1_saved + m5_saved
                for timeframe, saved in (("M1", m1_saved), ("M5", m5_saved)):
                    cur.execute("SELECT max(ts) AS latest,count(*) AS bars FROM public.market_bars WHERE symbol=%s AND timeframe=%s", (symbol, timeframe))
                    state = cur.fetchone()
                    result.append({"symbol": symbol, "timeframe": timeframe, "fetched_m1": len(candles), "closed_m1": len(complete),
                                   "upserted": saved, "latest": state["latest"].isoformat() if state["latest"] else None, "bars": state["bars"]})
    print(json.dumps({"source": SOURCE_VERSION, "status": "ONLINE", "upserted": total_saved, "rows": result}, ensure_ascii=False))
    print("VERDICT=MOEX_INDEX_ONLINE_V2_OK")


if __name__ == "__main__":
    main()
