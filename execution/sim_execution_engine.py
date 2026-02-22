from execution.execution_engine import BaseExecutionEngine
from core.events import FillEvent


class SimExecutionEngine(BaseExecutionEngine):
    def __init__(self, event_bus=None, price_resolver=None):
        self.event_bus = event_bus
        self.price_resolver = price_resolver

    def execute(self, order):
        """
        Simulate immediate fill at resolved price.
        """

        if self.price_resolver:
            price = self.price_resolver(order.symbol)
        else:
            price = order.price or 0.0

        fill = FillEvent(
            event_id=str(uuid4()),
            fill_id=str(uuid4()),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            qty=qty,
            price=float(market_price),
            commission=0.0,
            timestamp=ts,
        )
        if self.event_bus:
            self.event_bus.publish(fill)

        return fill