from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TradeContextEnvelope:
    trade_id: int
    ts: datetime
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    side: str
    qty: float
    price: float

    regime: dict[str, Any]
    risk: dict[str, Any]
    runtime: dict[str, Any]
    execution: dict[str, Any]
    strategy_context: dict[str, Any]
    feature_snapshot: dict[str, Any]

    context_quality: str
    missing_fields: list[str]
