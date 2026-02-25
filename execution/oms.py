# execution/oms.py

from execution.order_model import Order
from uuid import uuid4


class OMS:

    def __init__(self, storage, execution_engine):
        self.storage = storage
        self.execution_engine = execution_engine

    # ------------------------------------------------------------
    # ------------------- Order Creation -------------------------
    # ------------------------------------------------------------

    def create_order(self, signal_event, qty: float = 1.0):

        order = Order.create_from_signal(signal_event, qty=qty)

        self.storage.save_order(order)

        return order

    # ------------------------------------------------------------
    # ------------------- Order Processing -----------------------
    # ------------------------------------------------------------

    def process_order(self, order, market_price, ts):

        fills = self.execution_engine.execute(order, market_price, ts)

        for fill in fills:
            self.storage.save_fill(fill)

        self.storage.update_order_status(
            order_id=order.order_id,
            status=order.status,
            filled_qty=order.filled_qty,
            avg_fill_price=order.avg_fill_price,
            ts=order.updated_ts,
        )

        return fills

    # ------------------------------------------------------------
    # ---------------- SignalIntent Support ----------------------
    # ------------------------------------------------------------

    def create_order_from_intent(self, intent):
        """
        Convert SignalIntent → Order.
        Currently proxies to existing create_order logic.
        """

        return self.create_order(intent)
