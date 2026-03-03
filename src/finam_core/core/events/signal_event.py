from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from .base_event import BaseEvent


@dataclass(frozen=True)
class SignalEvent(BaseEvent):
    event_id: str
    symbol: str
    signal_type: str
    strength: float
    timestamp: datetime
    features: Optional[Dict] = None


@dataclass(frozen=True)
class StrategySignalEvent(SignalEvent):
    pass