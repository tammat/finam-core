# -*- coding: utf-8 -*-
"""
finam_core.scripts.load_history

Загрузка исторических баров в SQLite чанками (устойчиво к 429 Too Many Requests).

ENV:
- SYMBOL          (например BRM6@RTSX)
- TIMEFRAME       (M1/M5/M15/H1/D1)
- DAYS            (сколько дней назад, если нет RESUME или БД пустая)
- BARS_DB         (путь к sqlite)
- CHUNK_MINUTES   (размер чанка, например 180 = 3 часа)
- RESUME          (1/0) если 1 — стартуем от max(ts) в БД + 1 бар
- CHUNK_SLEEP_SEC (пауза между чанками, по умолчанию 1.0)
- MAX_RETRIES     (retry на RPC, по умолчанию 8)
- BACKOFF_SEC     (базовый backoff, по умолчанию 2.0)
- BACKOFF_MAX_SEC (макс backoff, по умолчанию 120)
"""

from __future__ import annotations

import os
import time
import math
import grpc
from datetime import datetime, timedelta, timezone

from finam_core.ingestion.history_loader import HistoryLoader
from finam_core.storage.sqlite import BarsSQLiteStorage


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default


def _tf_step(timeframe: str) -> timedelta:
    tf = timeframe.upper()
    if tf == "M1":
        return timedelta(minutes=1)
    if tf == "M5":
        return timedelta(minutes=5)
    if tf == "M15":
        return timedelta(minutes=15)
    if tf == "M30":
        return timedelta(minutes=30)
    if tf == "H1":
        return timedelta(hours=1)
    if tf == "H2":
        return timedelta(hours=2)
    if tf == "H4":
        return timedelta(hours=4)
    if tf == "D1" or tf == "D":
        return timedelta(days=1)
    # fallback
    return timedelta(minutes=1)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.replace(microsecond=0).isoformat()


def _db_max_ts(store: BarsSQLiteStorage, symbol: str, timeframe: str) -> str | None:
    cur = store.con.cursor()
    row = cur.execute(
        "SELECT max(ts) FROM bars WHERE symbol=? AND timeframe=?",
        (symbol, timeframe),
    ).fetchone()
    mx = row[0] if row else None
    return mx


def main() -> None:
    symbol = _env("SYMBOL", "BRM6@RTSX")
    timeframe = _env("TIMEFRAME", "M1").upper()
    days = int(_env("DAYS", "30"))
    db_path = _env("BARS_DB", "data/bars.sqlite")

    chunk_minutes = int(_env("CHUNK_MINUTES", "180"))
    resume = _env("RESUME", "1") == "1"

    sleep_sec = float(_env("CHUNK_SLEEP_SEC", "1.0"))
    max_retries = int(_env("MAX_RETRIES", "8"))
    backoff_base = float(_env("BACKOFF_SEC", "2.0"))
    backoff_max = float(_env("BACKOFF_MAX_SEC", "120"))

    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=days)

    loader = HistoryLoader(host=os.getenv("FINAM_API_HOST") or "api.finam.ru:443")
    store = BarsSQLiteStorage(db_path)

    try:
        if resume:
            mx = _db_max_ts(store, symbol, timeframe)
            if mx:
                mx_dt = datetime.fromisoformat(mx)
                start = mx_dt + _tf_step(timeframe)

        print(
            f"LOAD_HISTORY symbol={symbol} tf={timeframe} days={days} db={db_path} "
            f"chunk_min={chunk_minutes} resume={int(resume)} sleep={sleep_sec}s",
            flush=True,
        )
        print(f"RANGE start={_iso(start)} end={_iso(end)}", flush=True)

        total_written = 0
        total_minutes = max(1, int((end - start).total_seconds() // 60))
        total_chunks = max(1, int(math.ceil(total_minutes / float(chunk_minutes))))

        cur_start = start
        chunk_idx = 0

        while cur_start < end:
            chunk_idx += 1
            cur_end = min(end, cur_start + timedelta(minutes=chunk_minutes))

            print(f"[{chunk_idx}/{total_chunks}] fetch {_iso(cur_start)} .. {_iso(cur_end)} ...", flush=True)

            # retry/backoff на сам fetch
            attempt = 0
            while True:
                try:
                    bars = loader.load(symbol, timeframe, cur_start, cur_end)
                    break
                except grpc.RpcError as e:
                    attempt += 1
                    code = e.code()
                    msg = (e.details() or "").strip()

                    # 429 / Too many requests
                    if code == grpc.StatusCode.RESOURCE_EXHAUSTED:
                        wait = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                        # При 429 обычно помогает более длинная пауза
                        wait = max(wait, 10.0)
                        print(f"  429 RESOURCE_EXHAUSTED: {msg} -> sleep {wait:.1f}s (attempt {attempt}/{max_retries})", flush=True)
                        time.sleep(wait)
                        if attempt >= max_retries:
                            raise
                        continue

                    # временная сеть
                    if code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
                        wait = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                        print(f"  NET {code.name}: {msg} -> sleep {wait:.1f}s (attempt {attempt}/{max_retries})", flush=True)
                        time.sleep(wait)
                        if attempt >= max_retries:
                            raise
                        continue

                    # прочее — не маскируем
                    raise

                except Exception as e:
                    attempt += 1
                    wait = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                    print(f"  ERR {type(e).__name__}: {e} -> sleep {wait:.1f}s (attempt {attempt}/{max_retries})", flush=True)
                    time.sleep(wait)
                    if attempt >= max_retries:
                        raise

            # записываем
            n = store.upsert_bars(symbol=symbol, timeframe=timeframe, bars=bars)
            total_written += n
            print(f"  got={len(bars)} written={n} total_written={total_written}", flush=True)

            cur_start = cur_end
            if sleep_sec > 0:
                time.sleep(sleep_sec)

        print("DONE load_history", flush=True)

    finally:
        try:
            loader.close()
        except Exception:
            pass
        try:
            store.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
