# -*- coding: utf-8 -*-
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc
from finam_proto.google.type import interval_pb2


# Русский коммент: по умолчанию пишем бары в локальный SQLite.
DEFAULT_DB_PATH = os.getenv("BARS_DB") or "data/bars.sqlite"


def _ts(dt: datetime) -> Timestamp:
    t = Timestamp()
    t.FromDatetime(dt)
    return t


def _ensure_db(db_path: str) -> sqlite3.Connection:
    """Русский коммент: создаём БД и таблицу bars, если их ещё нет."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
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
    """Русский коммент: upsert по первичному ключу (symbol,timeframe,ts)."""
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


def main():
    host = os.getenv("FINAM_API_HOST") or "api.finam.ru:443"
    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
    tf_str = (os.getenv("TIMEFRAME") or "M5").upper()
    days = int(os.getenv("DAYS") or "5")
    # Русский коммент: Finam часто режет диапазон для M1 (и некоторых ТФ). По умолчанию дробим запрос.
    max_days_per_call = float(os.getenv("MAX_DAYS_PER_CALL") or ("7" if tf_str == "M1" else "30"))
    max_days_per_call = max(0.25, max_days_per_call)
    db_path = os.getenv("BARS_DB") or DEFAULT_DB_PATH

    # Русский коммент: небольшой буфер, чтобы не запрашивать «будущее»/незакрытый бар
    end = datetime.now(timezone.utc) - timedelta(seconds=30)
    start = end - timedelta(days=days)

    # Русский коммент: маппим строковый таймфрейм в enum протобуфа
    # Обычно в pb2 это что-то вроде TIME_FRAME_M1/TIME_FRAME_M5/...
    enum_name = f"TIME_FRAME_{tf_str}"
    if not hasattr(md_pb2.TimeFrame, enum_name):
        raise RuntimeError(f"Unknown TIMEFRAME={tf_str}. Expected one of: {[n for n in dir(md_pb2.TimeFrame) if n.startswith('TIME_FRAME_')]}")

    timeframe = getattr(md_pb2.TimeFrame, enum_name)

    jwt = FinamTokenManager().get_token()
    md = [("authorization", f"Bearer {jwt}")]

    ch = grpc.secure_channel(host, grpc.ssl_channel_credentials())
    stub = md_grpc.MarketDataServiceStub(ch)

    con = _ensure_db(db_path)
    cur = con.cursor()

    def _bars_from_resp(r):
        # Русский коммент: в разных версиях API поле может называться bars/items.
        return getattr(r, "bars", None) or getattr(r, "items", None) or r

    def _fetch_chunk(s: datetime, e: datetime):
        req = md_pb2.BarsRequest(
            symbol=symbol,
            timeframe=timeframe,
            interval=interval_pb2.Interval(
                start_time=_ts(s),
                end_time=_ts(e),
            ),
        )
        return stub.Bars(req, metadata=md)

    # Русский коммент: дробим диапазон на окна max_days_per_call, чтобы избежать INVALID_ARGUMENT
    chunks = []
    cursor_end = end
    while cursor_end > start:
        cursor_start = max(start, cursor_end - timedelta(days=max_days_per_call))
        chunks.append((cursor_start, cursor_end))
        cursor_end = cursor_start

    # Русский коммент: грузим по порядку от старых к новым
    chunks.reverse()

    # Русский коммент: дальше будем подставлять bars из каждого чанка

    cnt = 0
    batch = 0

    for (cs, ce) in chunks:
        try:
            resp = _fetch_chunk(cs, ce)
        except grpc.RpcError as e:
            # Русский коммент: если диапазон не принимается — пробуем автоматически уменьшить окно (до 6 часов)
            if e.code() == grpc.StatusCode.INVALID_ARGUMENT and max_days_per_call > (6 / 24):
                if os.getenv("MD_DEBUG") == "1":
                    print(f"BARS INVALID_ARGUMENT for range {cs.isoformat()}..{ce.isoformat()} — shrinking window", flush=True)
                # дробим текущий чанк пополам и продолжаем
                mid = cs + (ce - cs) / 2
                # защита от бесконечного цикла
                if mid <= cs + timedelta(minutes=1):
                    raise
                chunks.extend([(cs, mid), (mid, ce)])
                chunks.sort(key=lambda x: x[0])
                continue
            raise

        bars = _bars_from_resp(resp)

        for b in bars:
            ts = b.timestamp.ToDatetime().isoformat() if hasattr(b, "timestamp") else None
            if not ts:
                continue

            o = float(getattr(getattr(b, "open", None), "value", 0.0) or 0.0)
            h = float(getattr(getattr(b, "high", None), "value", 0.0) or 0.0)
            l = float(getattr(getattr(b, "low", None), "value", 0.0) or 0.0)
            c = float(getattr(getattr(b, "close", None), "value", 0.0) or 0.0)
            v = float(getattr(getattr(b, "volume", None), "value", 0.0) or 0.0)

            _upsert_bar(
                con,
                symbol=symbol,
                timeframe=tf_str,
                ts_iso=ts,
                o=o,
                h=h,
                l=l,
                c=c,
                v=v,
            )

            cnt += 1
            batch += 1

            if cnt <= 5:
                print(ts, o, h, l, c, v)

            # Русский коммент: коммитим пачками, чтобы не тормозить на каждом INSERT.
            if batch >= 500:
                con.commit()
                batch = 0

    if batch > 0:
        con.commit()

    try:
        con.close()
    except Exception:
        pass

    print("BARS:", cnt)
    print("SQLITE:", db_path)

    try:
        ch.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()