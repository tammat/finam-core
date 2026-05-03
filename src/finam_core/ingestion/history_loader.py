# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import psycopg2
from psycopg2.extras import execute_values


@dataclass(frozen=True)
class HistoryBar:
    symbol: str
    timeframe: str
    ts: datetime
    open: float | None
    high: float | None
    low: float | None
    close_price: float
    volume: float


class HistoryLoader:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("DATABASE_URL") or (
            f"postgresql://{os.getenv('DB_USER','finam')}:{os.getenv('DB_PASSWORD','finam')}"
            f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','finam')}"
        )

    def read_csv(self, path: str | Path, symbol: str, timeframe: str = "M1") -> list[HistoryBar]:
        bars = []
        with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            reader = csv.DictReader(fh, dialect=dialect)

            for row in reader:
                try:
                    ts_raw = row.get("ts") or f"{row.get('<DATE>')} {row.get('<TIME>')}"
                    ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)

                    bars.append(
                        HistoryBar(
                            symbol=symbol,
                            timeframe=timeframe,
                            ts=ts,
                            open=float(row.get("open") or row.get("<OPEN>")),
                            high=float(row.get("high") or row.get("<HIGH>")),
                            low=float(row.get("low") or row.get("<LOW>")),
                            close_price=float(row.get("close") or row.get("close_price") or row.get("<CLOSE>")),
                            volume=float(row.get("volume") or row.get("<VOL>") or 0),
                        )
                    )
                except Exception:
                    continue
        return bars

    def load_bars(self, bars: Sequence[HistoryBar], batch_size: int = 1000) -> int:
        if not bars:
            return 0

        rows = [
            (b.symbol, b.timeframe, b.open, b.high, b.low, b.close_price, b.volume, b.ts)
            for b in bars
        ]

        sql = """
            INSERT INTO market_data (
                symbol, timeframe, open, high, low, close_price, volume, ts
            )
            VALUES %s
            ON CONFLICT (symbol, timeframe, ts) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume
        """

        written = 0
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for start in range(0, len(rows), batch_size):
                    chunk = rows[start:start + batch_size]
                    execute_values(cur, sql, chunk)
                    written += len(chunk)
            conn.commit()

        return written

    def load_csv(self, path: str | Path, symbol: str, timeframe: str = "M1", batch_size: int = 1000) -> int:
        return self.load_bars(self.read_csv(path, symbol, timeframe), batch_size)
