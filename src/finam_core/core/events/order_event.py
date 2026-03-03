from dataclasses import dataclass
from .base_event import BaseEvent
from .fill_event import FillEvent


@dataclass(frozen=True)
class OrderEvent(BaseEvent):
    symbol: str
    side: str
    qty: float


@dataclass(frozen=True)
class OrderCreateRequestedEvent(OrderEvent):
    price: float
    order_type: str


@dataclass(frozen=True)
class OrderCreatedEvent(OrderEvent):
    price: float
    order_id: str | None = None



@dataclass(frozen=True)
class ExecutionEvent(FillEvent):
    pass