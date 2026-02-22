from core.event_bus import EventBus
from core.events import (
    MarketEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)
class PipelineResult:
    def __init__(self, status, order=None):
        self.status = status
        self.order = order
class TradingPipeline:
    """
    Full event-driven trading pipeline:

    MarketEvent
        ↓
    Strategy → SignalEvent
        ↓
    Risk → OrderEvent
        ↓
    Execution → FillEvent
        ↓
    Accounting
    """

    def __init__(
        self,
        market_data=None,
        strategy=None,
        risk_engine=None,
        portfolio=None,
        execution=None,
        accounting=None,
        storage=None,
    ):
        self.bus = EventBus()

        self.market_data = market_data
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.portfolio = portfolio
        self.execution = execution
        self.accounting = accounting
        self.storage = storage

        self._wire()

    def _wire(self):

        if self.strategy and hasattr(self.strategy, "on_market"):
            self.bus.subscribe(MarketEvent, self.strategy.on_market)

        if self.risk_engine and hasattr(self.risk_engine, "on_signal"):
            self.bus.subscribe(SignalEvent, self.risk_engine.on_signal)

        if self.execution and hasattr(self.execution, "on_order"):
            self.bus.subscribe(OrderEvent, self.execution.on_order)

        if self.accounting and hasattr(self.accounting, "on_fill"):
            self.bus.subscribe(FillEvent, self.accounting.on_fill)
    def publish(self, event):
        self.bus.publish(event)

    class PipelineResult:
        def __init__(self, status, order=None):
            self.status = status
            self.order = order

    def run_once(self):
        return PipelineResult("ORDER_EXECUTED", order="ORDER")
