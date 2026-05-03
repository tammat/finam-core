# -*- coding: utf-8 -*-
"""
MTFBarAggregator — агрегатор тиков/котировок в M1/M5/M15 свечи.
Русский комментарий: слой данных, стратегия и execution сюда не встроены.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import floor


@dataclass(frozen=True)
class MTFBar:
    symbol: str
    timeframe: str
    ts: datetime
    open: float
    high: float
    low: float
    close_price: float
    volume: float


class MTFBarAggregator:
    def __init__(self, timeframes: tuple[str, ...] = ("M1", "M5", "M15")) -> None:
        self.timeframes = timeframes
        self._active: dict[tuple[str, str], MTFBar] = {}

    @staticmethod
    def _minutes(timeframe: str) -> int:
        if not timeframe.startswith("M"):
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return int(timeframe[1:])

    @staticmethod
    def _bucket(ts: datetime, minutes: int) -> datetime:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts = ts.astimezone(timezone.utc)
        minute = floor(ts.minute / minutes) * minutes
        return ts.replace(minute=minute, second=0, microsecond=0)

    def update(self, symbol: str, price: float, volume: float, ts: datetime) -> list[MTFBar]:
        closed: list[MTFBar] = []

        for tf in self.timeframes:
            bucket_ts = self._bucket(ts, self._minutes(tf))
            key = (symbol, tf)
            current = self._active.get(key)

            if current is None:
                self._active[key] = MTFBar(symbol, tf, bucket_ts, price, price, price, price, volume)
                continue

            if current.ts != bucket_ts:
                closed.append(current)
                self._active[key] = MTFBar(symbol, tf, bucket_ts, price, price, price, price, volume)
                continue

            self._active[key] = MTFBar(
                symbol=symbol,
                timeframe=tf,
                ts=current.ts,
                open=current.open,
                high=max(current.high, price),
                low=min(current.low, price),
                close_price=price,
                volume=current.volume + volume,
            )

        return closed
