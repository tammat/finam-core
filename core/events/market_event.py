from dataclasses import dataclass
from datetime import datetime
from .base_event import BaseEvent


@dataclass
class MarketEvent(BaseEvent):
    symbol: str
    price: float