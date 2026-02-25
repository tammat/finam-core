# domain/fill_event.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class FillEvent:
    fill_id: str
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float = 0.0
    order_id: Optional[str] = None