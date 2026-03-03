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
from storage.postgres_event_store import PostgresEventStore
from execution.order_manager import OrderManager

class TradingEngine:
    """
    Fully event-driven deterministic trading pipeline.
    EventStore is the consistency boundary.
    Shadow replay validation enabled.
    """

    def __init__(
            self,
            portfolio_manager=None,
            order_manager=None,
            risk_engine=None,
            portfolio_manager_cls=None,
            event_store=None,
            snapshot_store=None,
            dsn=None,
            event_bus=None,
    ):
        from core.event_bus import EventBus
        from storage.postgres_event_store import PostgresEventStore
        from storage.postgres_snapshot_store import PostgresSnapshotStore

        # -------------------------
        # Event Store
        # -------------------------
        if event_store is not None:
            self.event_store = event_store
        else:
            if dsn is None:
                raise ValueError("Either event_store or dsn must be provided")
            self.event_store = PostgresEventStore(dsn)

        # -------------------------
        # Snapshot Store
        # -------------------------
        if snapshot_store is not None:
            self.snapshot_store = snapshot_store
        elif dsn is not None:
            self.snapshot_store = PostgresSnapshotStore(dsn)
        else:
            self.snapshot_store = None

        # -------------------------
        # Event Bus
        # -------------------------
        self.bus = event_bus or EventBus(event_store=self.event_store)

        # -------------------------
        # Core components
        # -------------------------
        self.risk = risk_engine
        self.oms = order_manager

        # -------------------------
        # Portfolio
        # -------------------------
        if portfolio_manager is not None:
            self.live_pm = portfolio_manager
            self.portfolio_cls = portfolio_manager_cls or type(portfolio_manager)
        else:
            if portfolio_manager_cls is None:
                raise ValueError("portfolio_manager or portfolio_manager_cls required")
            self.portfolio_cls = portfolio_manager_cls
            self.live_pm = self.portfolio_cls()

        self.portfolio_stream = "portfolio-1"

        # -------------------------
        # Bootstrap
        # -------------------------
        if self.snapshot_store is not None:
            self._bootstrap_stream(self.portfolio_stream, self.live_pm)

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
    # Bootstrap (Snapshot + Tail Replay)
    # ---------------------------------------------------

    def _bootstrap_stream(self, stream: str, pm):
        """Restore PM state from latest snapshot (if any) and replay tail events."""
        snap = self.snapshot_store.load_latest(stream)

        if snap:
            state_dict = snap["state"]
            last_seq = snap["last_seq"]

            # Restore portfolio manager state (если есть поддержка)
            if hasattr(pm, "restore"):
                pm.restore(state_dict)
            elif hasattr(pm, "from_dict"):
                pm.from_dict(state_dict)
            else:
                # если PM не умеет восстанавливаться — игнорируем snapshot
                last_seq = 0

            if last_seq > 0:
                self.event_store.replay_from(
                    stream=stream,
                    from_seq=last_seq,
                    handler=pm.handle_event,
                )
                return

        # No snapshot (or snapshot not applicable): full replay
        self.event_store.replay_stream(stream=stream, handler=pm.handle_event)
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
        self.bus.publish(
            RiskCheckRequestedEvent(
                symbol=event.symbol,
                side=event.side,
                qty=event.qty,
                price=event.price,
            )
        )

    def _on_risk_check(self, event: RiskCheckRequestedEvent):
        allowed, reason = self.risk.validate(
            self.live_pm.compute_state(),
            event.symbol,
            event.side,
            event.qty,
            event.price,
        )

        if allowed:
            self.bus.publish(
                RiskApprovedEvent(
                    symbol=event.symbol,
                    side=event.side,
                    qty=event.qty,
                    price=event.price,
                )
            )
        else:
            self.bus.publish(
                RiskRejectedEvent(
                    symbol=event.symbol,
                    side=event.side,
                    qty=event.qty,
                    price=event.price,
                    reason=reason,
                )
            )

    def _on_risk_approved(self, event: RiskApprovedEvent):
        order = self.oms.create_order(
            symbol=event.symbol,
            side=event.side,
            qty=event.qty,
            price=event.price,
        )

        self.bus.publish(
            ExecutionEvent(
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                price=order.price,
                commission=order.commission,
                realized_pnl=0.0,
            )
        )
    def _on_execution(self, event: ExecutionEvent):
        # --- LIVE UPDATE ---
        self.live_pm.on_fill(event.fill)
        live_state = self.live_pm.compute_state()

        # --- SHADOW REPLAY VALIDATION ---
        shadow_pm = self.portfolio_cls()

        self.event_store.replay_stream(
            stream="portfolio-1",
            handler=lambda e: shadow_pm.handle_event(e),
        )

        shadow_state = shadow_pm.compute_state()
        # ---- SNAPSHOT ----
        latest_seq = self.event_store.get_latest_seq("portfolio-1")

        if latest_seq % self.snapshot_interval == 0:
            self.snapshot_store.save(
                stream="portfolio-1",
                last_seq=latest_seq,
                state=live_state.to_dict(),
            )
        if live_state != shadow_state:
            raise RuntimeError("STATE_DIVERGENCE_DETECTED")

        self.bus.publish(PortfolioUpdatedEvent(live_state))