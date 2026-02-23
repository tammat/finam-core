from core.event_bus import EventBus
from core.events import (
    StrategySignalEvent,
    OrderCreateRequestedEvent,
    RiskCheckRequestedEvent,
    RiskApprovedEvent,
    RiskRejectedEvent,
    ExecutionEvent,
    PortfolioUpdatedEvent,
)


class TradingEngine:
    """
    Fully event-driven deterministic trading pipeline.
    No direct cross-module calls.
    All flow routed via EventBus.
    """

    def __init__(self, risk_engine, order_manager, portfolio_manager):
        self.bus = EventBus()
        self.risk = risk_engine
        self.oms = order_manager
        self.portfolio = portfolio_manager

        self._wire()

    # ---------------------------------------------------
    # Wiring
    # ---------------------------------------------------

    def _wire(self):
        self.bus.subscribe(StrategySignalEvent, self._on_signal)
        self.bus.subscribe(OrderCreateRequestedEvent, self._on_order_create)
        self.bus.subscribe(RiskCheckRequestedEvent, self._on_risk_check)
        self.bus.subscribe(RiskApprovedEvent, self._on_risk_approved)
        self.bus.subscribe(ExecutionEvent, self._on_execution)

    # ---------------------------------------------------
    # Public API
    # ---------------------------------------------------

    def process_signal(self, symbol: str, side: str, qty: float, price: float):
        self.bus.publish(
            StrategySignalEvent(symbol, side, qty, price)
        )

    # ---------------------------------------------------
    # Handlers
    # ---------------------------------------------------

    def _on_signal(self, event: StrategySignalEvent):
        self.bus.publish(
            OrderCreateRequestedEvent(
                event.symbol,
                event.side,
                event.qty,
                event.price,
            )
        )

    def _on_order_create(self, event: OrderCreateRequestedEvent):
        order = self.oms.create_order(
            order_id=f"auto_{id(event)}",
            symbol=event.symbol,
            side=event.side,
            qty=event.qty,
            price=event.price,
        )
        self.bus.publish(RiskCheckRequestedEvent(order))

    def _on_risk_check(self, event: RiskCheckRequestedEvent):
        portfolio_state = self.portfolio.compute_state()

        allowed, reason = self.risk.validate(
            portfolio_state=portfolio_state,
            symbol=event.order.symbol,
            side=event.order.side,
            qty=event.order.qty,
            price=event.order.price,
        )

        if allowed:
            self.bus.publish(RiskApprovedEvent(event.order))
        else:
            self.bus.publish(RiskRejectedEvent(event.order, reason))

    def _on_risk_approved(self, event: RiskApprovedEvent):
        self.oms.accept_order(event.order.id)

        # Deterministic immediate fill simulation
        fill = event.order
        self.bus.publish(ExecutionEvent(fill))

    def _on_execution(self, event: ExecutionEvent):
        self.portfolio.on_fill(event.fill)
        state = self.portfolio.compute_state()
        self.bus.publish(PortfolioUpdatedEvent(state))