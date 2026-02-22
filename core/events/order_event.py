from dataclasses import dataclass
from datetime import datetime
from .base_event import BaseEvent


@dataclass
class OrderEvent(BaseEvent):
    symbol: str
    side: str
    qty: float
