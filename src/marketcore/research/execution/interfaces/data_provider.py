from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MarketBar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketBars:
    symbol: str
    timeframe: str
    source: str
    bars: list[MarketBar]

    @property
    def count(self) -> int:
        return len(self.bars)


class DataProvider(Protocol):
    def load_market_data(
        self,
        symbol: str,
        timeframe: str,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
        parameters: dict | None = None,
    ) -> MarketBars:
        ...
