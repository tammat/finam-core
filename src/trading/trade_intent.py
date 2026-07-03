from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TradeIntent:
    symbol: str
    timeframe: str
    strategy: str
    side: str
    quantity_requested: Decimal
    source_signal_id: str
