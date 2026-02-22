from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from .base_event import BaseEvent


@dataclass
class SignalEvent(BaseEvent):
    symbol: str
    signal_type: str
    strength: float
    features: Optional[Dict[str, Any]] = None