# -*- coding: utf-8 -*-
"""
BarsSQLiteStorage — хранение исторических свечей в SQLite.

Схема:
bars(symbol TEXT, timeframe TEXT, ts TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)
UNIQUE(symbol, timeframe, ts) — upsert по ключу.

ts храним ISO строкой (UTC), совместимо с твоими backtest_runner.py и grid_*.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def _ts_to_iso(ts: Any) -> str:
    """
    Поддерживаем:
    - str (ISO)
    - datetime
    - protobuf Timestamp-подобные объекты: .seconds (+ .nanos)
    """
    if ts is None:
        raise ValueError("bar.ts is None")

    if isinstance(ts, str):
        # уже ISO
        return ts

    if isinstance(ts, datetime):
        dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    # protobuf Timestamp (google.protobuf.timestamp_pb2.Timestamp)
    sec = getattr(ts, "seconds", None)
    if sec is not None:
        nanos = getattr(ts, "nanos", 0) or 0
        dt = datetime.fromtimestamp(int(sec) + float(nanos) / 1e9, tz=timezone.utc)
        # чтобы было стабильно как в твоих примерах: секундная точность
        dt = dt.replace(microsecond=0)
        return dt.isoformat()

    # fallback
    return str(ts)


def _dec_to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    # Finam Decimal часто = { value: "102.31" }
    v = getattr(x, "value", None)
    if v is not None:
        try:
            return float(v)
        except Exception:
            return None
    try:
        return float(x)
    except Exception:
        return None


class BarsSQLiteStorage:
    def __init__(self, path: str = "data/bars.sqlite"):
        self.path = path
        self.con = sqlite3.connect(self.path)
        self.con.execute("PRAGMA journal_mode=WAL;")
        self.con.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def close(self) -> None:
        try:
            self.con.close()
        except Exception:
            pass

    def _init_schema(self) -> None:
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS bars (
                symbol   TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                ts       TEXT NOT NULL,
                open     REAL,
                high     REAL,
                low      REAL,
                close    REAL,
                volume   REAL,
                PRIMARY KEY(symbol, timeframe, ts)
            )
            """
        )
        self.con.execute("CREATE INDEX IF NOT EXISTS ix_bars_sym_tf_ts ON bars(symbol, timeframe, ts)")
        self.con.commit()

    def upsert_bars(self, *, symbol: str, timeframe: str, bars: Iterable[Dict[str, Any]]) -> int:
        """
        bars: list[dict] как из HistoryLoader:
          {'ts': ..., 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ...}

        Возвращает: сколько строк обработали (attempted).
        """
        rows: List[tuple] = []
        for b in bars:
            ts = _ts_to_iso(b.get("ts"))
            o = _dec_to_float(b.get("open"))
            h = _dec_to_float(b.get("high"))
            l = _dec_to_float(b.get("low"))
            c = _dec_to_float(b.get("close"))
            v = _dec_to_float(b.get("volume"))
            rows.append((symbol, timeframe, ts, o, h, l, c, v))

        if not rows:
            return 0

        self.con.executemany(
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
            rows,
        )
        self.con.commit()
        return len(rows)
