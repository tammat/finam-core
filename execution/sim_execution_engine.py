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
            symbol=order.symbol,
            quantity=order.quantity,
            price=price,
            side=order.side,
        )

        if self.event_bus:
            self.event_bus.publish(fill)

        return fill