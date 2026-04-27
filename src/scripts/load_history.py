# -*- coding: utf-8 -*-
"""
load_history.py — gRPC Bars -> SQLite

Режимы:
- days: последние N дней (UTC)
- start/end: явный диапазон (UTC)
- resume: продолжить с MAX(ts) из SQLite по (symbol,timeframe)

Стратегия устойчивости:
- грузим чанками по времени (например M1 по 1-2 дня)
- при INVALID_ARGUMENT уменьшаем чанк вдвое, пока не пройдет или не достигнем минимума
"""

import os
import sqlite3
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc
from finam_proto.google.type import interval_pb2


DEFAULT_DB_PATH = os.getenv("BARS_DB") or "data/bars.sqlite"


# -------------------------
# Utils
# -------------------------
def _ts(dt: datetime) -> Timestamp:
    t = Timestamp()
    t.FromDatetime(dt)
    return t


def _parse_iso(s: str) -> datetime:
    # Русский коммент: принимаем ISO с/без timezone, приводим к UTC
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _tf_delta(tf: str) -> timedelta:
    tf = tf.upper()
    if tf == "M1":
        return timedelta(minutes=1)
    if tf == "M5":
        return timedelta(minutes=5)
    if tf == "M15":
        return timedelta(minutes=15)
    if tf == "H1":
        return timedelta(hours=1)
    if tf == "D1":
        return timedelta(days=1)
    raise RuntimeError(f"Unsupported TIMEFRAME={tf} (expected: M1,M5,M15,H1,D1)")


def _default_chunk(tf: str) -> timedelta:
    """
    Русский коммент: дефолтные чанки под ограничения API.
    Если API позволяет больше — можно увеличить.
    """
    tf = tf.upper()
    if tf == "M1":
        return timedelta(days=2)      # безопасно
    if tf == "M5":
        return timedelta(days=10)
    if tf == "M15":
        return timedelta(days=30)
    if tf == "H1":
        return timedelta(days=180)
    if tf == "D1":
        return timedelta(days=365 * 5)
    return timedelta(days=2)


# -------------------------
# SQLite
# -------------------------
def _ensure_db(db_path: str) -> sqlite3.Connection:
    """Русский коммент: создаём БД и таблицу bars, если их ещё нет."""
    d = os.path.dirname(db_path)
    if d:
        os.makedirs(d, exist_ok=True)

    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS bars (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            ts TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, timeframe, ts)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_bars_symbol_tf_ts ON bars(symbol, timeframe, ts)")
    return con


def _upsert_bar(
    con: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    ts_iso: str,
    o: float,
    h: float,
    l: float,
    c: float,
    v: float,
) -> None:
    con.execute(
        """
        INSERT INTO bars(symbol, timeframe, ts, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, timeframe, ts) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume
        """,
        (symbol, timeframe, ts_iso, o, h, l, c, v),
    )


def _max_ts(con: sqlite3.Connection, symbol: str, timeframe: str) -> str | None:
    cur = con.cursor()
    cur.execute("SELECT MAX(ts) FROM bars WHERE symbol=? AND timeframe=?", (symbol, timeframe))
    row = cur.fetchone()
    return row[0] if row and row[0] else None


# -------------------------
# gRPC Bars fetch
# -------------------------
@dataclass
class BarRow:
    ts_iso: str
    o: float
    h: float
    l: float
    c: float
    v: float


def _fetch_bars(stub, md_meta, symbol: str, timeframe_enum, start: datetime, end: datetime):
    req = md_pb2.BarsRequest(
        symbol=symbol,
        timeframe=timeframe_enum,
        interval=interval_pb2.Interval(start_time=_ts(start), end_time=_ts(end)),
    )
    return stub.Bars(req, metadata=md_meta)


def _iter_resp_bars(resp):
    # Русский коммент: обычно resp.bars — repeated Bar
    bars = getattr(resp, "bars", None)
    if bars is not None:
        return bars
    items = getattr(resp, "items", None)
    if items is not None:
        return items
    # fallback: если resp и есть iterable
    return resp


def _bar_to_row(b) -> BarRow | None:
    ts = b.timestamp.ToDatetime().isoformat() if hasattr(b, "timestamp") else None
    if not ts:
        return None

    def _val(x):
        try:
            return float(getattr(x, "value", 0.0) or 0.0)
        except Exception:
            return 0.0

    o = _val(getattr(b, "open", None))
    h = _val(getattr(b, "high", None))
    l = _val(getattr(b, "low", None))
    c = _val(getattr(b, "close", None))
    v = _val(getattr(b, "volume", None))

    return BarRow(ts_iso=ts, o=o, h=h, l=l, c=c, v=v)


# -------------------------
# Main loader logic
# -------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
    p.add_argument("--timeframe", default=(os.getenv("TIMEFRAME") or "M1").upper())
    p.add_argument("--days", type=int, default=int(os.getenv("DAYS") or "5"))
    p.add_argument("--start", default=os.getenv("START") or "")
    p.add_argument("--end", default=os.getenv("END") or "")
    p.add_argument("--db", default=os.getenv("BARS_DB") or DEFAULT_DB_PATH)
    p.add_argument("--resume", action="store_true", default=(os.getenv("RESUME", "1") == "1"))
    p.add_argument("--no-resume", dest="resume", action="store_false")
    p.add_argument("--chunk-minutes", type=int, default=int(os.getenv("CHUNK_MINUTES") or "0"))
    args = p.parse_args()

    host = os.getenv("FINAM_API_HOST") or "api.finam.ru:443"
    symbol = args.symbol
    tf_str = args.timeframe.upper()

    # timeframe enum
    enum_name = f"TIME_FRAME_{tf_str}"
    if not hasattr(md_pb2.TimeFrame, enum_name):
        raise RuntimeError(f"Unknown TIMEFRAME={tf_str}")

    timeframe_enum = getattr(md_pb2.TimeFrame, enum_name)

    # range
    if args.start and args.end:
        start = _parse_iso(args.start)
        end = _parse_iso(args.end)
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=args.days)

    if end <= start:
        raise RuntimeError("Invalid range: end <= start")

    # db + resume
    con = _ensure_db(args.db)

    if args.resume:
        last_ts = _max_ts(con, symbol, tf_str)
        if last_ts:
            # Русский коммент: продолжаем со следующего бара
            start2 = _parse_iso(last_ts) + _tf_delta(tf_str)
            if start2 < end:
                start = start2

    # chunk setup
    if args.chunk_minutes > 0:
        chunk = timedelta(minutes=args.chunk_minutes)
    else:
        chunk = _default_chunk(tf_str)

    # grpc init
    jwt = FinamTokenManager().get_token()
    md_meta = [("authorization", f"Bearer {jwt}")]

    ch = grpc.secure_channel(host, grpc.ssl_channel_credentials())
    stub = md_grpc.MarketDataServiceStub(ch)

    # load loop
    total = 0
    printed = 0

    cur_start = start
    min_chunk = timedelta(hours=3) if tf_str in ("M1", "M5") else timedelta(days=1)

    while cur_start < end:
        cur_end = min(cur_start + chunk, end)

        # Русский коммент: адаптивное уменьшение чанка при INVALID_ARGUMENT
        local_chunk = cur_end - cur_start

        while True:
            try:
                resp = _fetch_bars(stub, md_meta, symbol, timeframe_enum, cur_start, cur_start + local_chunk)
                bars = _iter_resp_bars(resp)

                batch = 0
                for b in bars:
                    row = _bar_to_row(b)
                    if not row:
                        continue

                    _upsert_bar(
                        con,
                        symbol=symbol,
                        timeframe=tf_str,
                        ts_iso=row.ts_iso,
                        o=row.o, h=row.h, l=row.l, c=row.c, v=row.v,
                    )
                    total += 1
                    batch += 1

                    if printed < 5:
                        print(row.ts_iso, row.o, row.h, row.l, row.c, row.v)
                        printed += 1

                    if batch >= 500:
                        con.commit()
                        batch = 0

                if batch > 0:
                    con.commit()

                # успешно — выходим из inner retry
                break

            except grpc.RpcError as e:
                msg = str(e)
                if "INVALID_ARGUMENT" in msg and "Invalid date range" in msg:
                    # уменьшаем чанк
                    if local_chunk <= min_chunk:
                        raise RuntimeError(
                            f"Invalid date range even for min_chunk={min_chunk}. "
                            f"Try smaller --chunk-minutes. Range: {cur_start.isoformat()}..{(cur_start+local_chunk).isoformat()}"
                        ) from e
                    local_chunk = local_chunk / 2
                    continue
                raise

        # следующий чанк
        cur_start = cur_start + local_chunk

    try:
        con.close()
    except Exception:
        pass

    try:
        ch.close()
    except Exception:
        pass

    print("BARS:", total)
    print("SQLITE:", args.db)
    print("RANGE:", start.isoformat(), "->", end.isoformat())


if __name__ == "__main__":
    main()
