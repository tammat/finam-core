from uuid import uuid4
from datetime import datetime, UTC

from execution.order_model import Order, OrderStatus
from domain.events import FillEvent


class OMS:
    def __init__(self, storage):
        self.storage = storage

    # -------------------------
    # Create order from signal
    # -------------------------
    def create_order(self, signal):

        ts = getattr(signal, "timestamp", datetime.now(UTC))

        order = Order(
            order_id=str(uuid4()),
            signal_event_id=getattr(signal, "event_id", str(uuid4())),
            symbol=signal.symbol,
            side=signal.signal_type,  # BUY/SELL or LONG/SHORT depending on upstream mapping
            qty=float(getattr(signal, "qty", 1.0)),
            price=float(getattr(signal, "price", 0.0)),
            status=OrderStatus.NEW,
            filled_qty=0.0,  # REQUIRED by your Order model
            created_ts=ts,
            updated_ts=ts,
        )

        if hasattr(self.storage, "log_order"):
            self.storage.log_order(
                order_id=order.order_id,
                signal_event_id=order.signal_event_id,
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                price=order.price,
                status=order.status,
                ts=order.created_ts,
            )

        return order

    # -------------------------
    # Execute order (SIM)
    # -------------------------
    def execute_order(self, order: Order, market_price: float | None = None, ts: datetime | None = None):

        ts = ts or datetime.now(UTC)
        fill_price = float(market_price if market_price is not None else order.price)

        order.status = OrderStatus.FILLED
        order.filled_qty = float(order.qty)  # REQUIRED by your Order model
        order.updated_ts = ts

        if hasattr(self.storage, "update_order_status"):
            self.storage.update_order_status(
                order_id=order.order_id,
                status=order.status,
                ts=ts,
            )

        fill = FillEvent(
            fill_id=str(uuid4()),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            qty=float(order.qty),
            price=fill_price,
            commission=0.0,
            timestamp=ts,
        )

        return fill