from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class Signal:
    symbol: str
    timeframe: str
    strategy_family: str
    signal_ts: datetime
    direction: str
    strength: float
    score: float
    confidence: float
