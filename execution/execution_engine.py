import time
from datetime import datetime, timezone

from core.events import FillEvent, OrderStatus
from execution.slippage_model import SlippageModel


VALID_TRANSITIONS = {
    "NEW": {"PENDING"},
    "PENDING": {"PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"},
    "PARTIALLY_FILLED": {"FILLED", "CANCELLED"},
    "FILLED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
}


class SimExecutionEngine:
    """
    Institutional-grade execution simulator.
    Includes:
    - strict state machine
    - idempotency protection
    - broker_order_id simulation
    - latency model
    - slippage model
    """

    def __init__(self, event_bus, price_resolver):
        self.event_bus = event_bus
        self.price_resolver = price_resolver

        self.active_orders = {}
        self.processed_orders = set()

        self.slippage_model = SlippageModel()

    # -------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------

    def execute(self, order):

        # 1️⃣ idempotency protection
        if order.event_id in self.processed_orders:
            return

        self.processed_orders.add(order.event_id)

        # 2️⃣ simulate broker order id
        order.broker_order_id = f"SIM-{order.event_id}"

        # 3️⃣ latency simulation
        time.sleep(0.01)

        # 4️⃣ transition NEW → PENDING
        self._transition(order, "PENDING")

        self.active_orders[order.event_id] = order

        # 5️⃣ simulate partial fill (50%)
        partial_qty = order.quantity * 0.5
        self._generate_fill(order, partial_qty)

        # 6️⃣ simulate remaining fill
        remaining = order.quantity - partial_qty
        if remaining > 0:
            self._generate_fill(order, remaining)

        # order removed when fully filled
        if order.status == OrderStatus.FILLED:
            self.active_orders.pop(order.event_id, None)

    def cancel(self, order_id):
        order = self.active_orders.get(order_id)
        if not order:
            return

        self._transition(order, "CANCELLED")
        self.active_orders.pop(order_id, None)

    # -------------------------------------------------
    # INTERNAL
    # -------------------------------------------------

    def _transition(self, order, new_status):

        current = order.status.value

        if new_status not in VALID_TRANSITIONS[current]:
            raise ValueError(
                f"Invalid order state transition: {current} → {new_status}"
            )

        order.status = OrderStatus(new_status)

    def _generate_fill(self, order, quantity):

        # 1️⃣ get mid price
        base_price = self.price_resolver(order.symbol)

        # 2️⃣ apply slippage
        execution_price = self.slippage_model.apply(
            base_price=base_price,
            quantity=quantity,
            side=order.side,
        )

        # 3️⃣ update filled qty
        order.filled_quantity += quantity

        if order.filled_quantity < order.quantity:
            self._transition(order, "PARTIALLY_FILLED")
        else:
            self._transition(order, "FILLED")

        # 4️⃣ publish fill
        self.event_bus.publish(
            FillEvent(
                symbol=order.symbol,
                side=order.side,
                quantity=quantity,
                price=execution_price,
                commission=0.0,
                timestamp=datetime.now(timezone.utc),
                meta={
                    "order_id": order.event_id,
                    "broker_order_id": order.broker_order_id,
                    "status": order.status.value,
                    "base_price": base_price,
                },
            )
        )