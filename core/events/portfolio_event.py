from dataclasses import dataclass
from .base_event import BaseEvent


@dataclass(frozen=True)
class PortfolioUpdatedEvent(BaseEvent):
    total_equity: float
    cash: float
    unrealized_pnl: float
    realized_pnl: float