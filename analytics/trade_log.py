# analytics/trade_log.py

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TradeRecord:
    timestamp: datetime
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float

    @property
    def pnl(self) -> float:
        direction = 1 if self.side == "BUY" else -1
        return (self.exit_price - self.entry_price) * direction * self.quantity