from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


SignalDirection = Literal["BUY", "SELL", "FLAT"]


@dataclass(frozen=True)
class StrategySignal:
    signal_ts: datetime
    direction: SignalDirection
    price: float
    confidence: float
    metadata: dict

    @property
    def is_trade_signal(self) -> bool:
        return self.direction in {"BUY", "SELL"}
