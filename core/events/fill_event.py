from dataclasses import dataclass
from datetime import datetime
from .base_event import BaseEvent


@dataclass
class FillEvent(BaseEvent):
    fill_id: str
    order_id: str
    symbol: str
    side: str
    qty: float
    price: float
    commission: float