from dataclasses import dataclass
from datetime import datetime


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