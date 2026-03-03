from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OrderExecution:
    symbol: str
    side: str
    quantity: float
    filled_price: Optional[float] = None
    status: str = "FILLED"