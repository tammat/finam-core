from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import uuid4


class OrderStatus(str, Enum):
    NEW = "NEW"
    WORKING = "WORKING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    order_id: str
    signal_event_id: str
    symbol: str
    side: str
    qty: float
    filled_qty: float
    price: float
    status: OrderStatus
    created_ts: datetime
    updated_ts: datetime

    @staticmethod
    def create(signal_event_id, symbol, side, qty, price, ts):
        return Order(
            order_id=str(uuid4()),
            signal_event_id=signal_event_id,
            symbol=symbol,
            side=side,
            qty=qty,
            filled_qty=0.0,
            price=price,
            status=OrderStatus.NEW,
            created_ts=ts,
            updated_ts=ts,
        )