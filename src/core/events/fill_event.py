from datetime import datetime, timezone
from uuid import uuid4

from .base_event import BaseEvent


class FillEvent(BaseEvent):
    def __init__(
        self,
        event_id=None,
        fill_id=None,
        order_id=None,
        symbol=None,
        side=None,
        qty=0.0,
        price=0.0,
        commission=0.0,
        timestamp=None,
    ):
        super().__init__(
            event_id=event_id or str(uuid4()),
            timestamp=timestamp or datetime.now(timezone.utc),
        )

        self.fill_id = fill_id or str(uuid4())
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.qty = float(qty)
        self.price = float(price)
        self.commission = float(commission)