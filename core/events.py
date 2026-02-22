from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any


@dataclass
class MarketEvent:
    symbol: str
    price: float
    volume: float
    timestamp: datetime


@dataclass
class SignalEvent:
    event_id: str
    symbol: str
    signal_type: str   # BUY / SELL / LONG / SHORT
    strength: float
    timestamp: datetime
    features: Dict[str, Any] | None = None


@dataclass
class FillEvent:
    fill_id: str
    order_id: str
    symbol: str
    side: str
    qty: float
    price: float
    commission: float
    timestamp: datetime