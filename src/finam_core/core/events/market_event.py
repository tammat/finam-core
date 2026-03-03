from dataclasses import dataclass, field
from uuid import uuid4, UUID
from datetime import datetime


@dataclass(frozen=True)
class MarketEvent:
    symbol: str
    price: float
    timestamp: datetime
    event_id: UUID = field(default_factory=uuid4)