import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any
from enum import Enum


class OrderStatus(str, Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Event:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = None

    def __post_init__(self):
        if self.correlation_id is None:
            self.correlation_id = self.event_id


@dataclass
class MarketEvent(Event):
    symbol: str = ""
    price: float = 0.0
    volume: float = 0.0
    timestamp: datetime = None


@dataclass
class SignalEvent(Event):
    symbol: str = ""
    signal_type: str = ""
    strength: float = 0.0
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = None


@dataclass
class RiskRejectedEvent(Event):
    symbol: str = ""
    signal_type: str = ""
    reason: str = ""
    timestamp: datetime = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderEvent(Event):
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    timestamp: datetime = None
    meta: Dict[str, Any] = field(default_factory=dict)
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0


@dataclass
class FillEvent(Event):
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    price: float = 0.0
    commission: float = 0.0
    timestamp: datetime = None
    meta: Dict[str, Any] = field(default_factory=dict)
@dataclass
class CancelOrderEvent(Event):
    order_id: str = ""
    timestamp: datetime = None