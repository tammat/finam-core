from dataclasses import dataclass
from .base_event import BaseEvent


@dataclass(frozen=True)
class RiskCheckRequestedEvent(BaseEvent):
    symbol: str
    qty: float


@dataclass(frozen=True)
class RiskApprovedEvent(BaseEvent):
    symbol: str
    qty: float


@dataclass(frozen=True)
class RiskRejectedEvent(BaseEvent):
    symbol: str
    qty: float
    reason: str