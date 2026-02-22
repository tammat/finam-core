from domain.events import MarketEvent, SignalEvent, FillEvent
from accounting.position_manager import PositionManager


class Engine:
    """
    Fund-grade Event Engine.
    Deterministic.
    Accounting-first.
    Execution-isolated.
    Storage-consistent.
    """

    def __init__(self, strategy, execution_engine, storage, risk_engine=None):
        self.strategy = strategy
        self.execution = execution_engine
        self.storage = storage
        self.risk_engine = risk_engine
        from accounting.portfolio_manager import PortfolioManager

        self.portfolio_manager = PortfolioManager(initial_cash=1_000_000)

        self.position_manager = PositionManager()
        from execution.oms import OMS

        self.oms = OMS(storage)
        self._running = False
        self._processed = 0

    # ============================================================
    # MAIN LOOP
    # ============================================================

    def run(self) -> int:
        self._running = True

        while self._running:
            event = self.strategy.next_event()
            if event is None:
                break

            try:
                self._route_event(event)
                self._processed += 1
            except Exception as e:
                # Fund-level engines never crash silently
                print(f"[ENGINE ERROR] {e}")
                raise

        return self._processed

    def stop(self):
        self._running = False

    # ============================================================
    # EVENT ROUTER
    # ============================================================

    def _route_event(self, event):

        if isinstance(event, MarketEvent):
            self._handle_market(event)

        elif isinstance(event, SignalEvent):
            self._handle_signal(event)

        elif isinstance(event, FillEvent):
            self._handle_fill(event)

        else:
            raise ValueError(f"Unknown event type: {type(event)}")

    # ============================================================
    # MARKET
    # ============================================================

    def _handle_market(self, event: MarketEvent):

        # 1. Persist market
        self.storage.log_market_price(
            symbol=event.symbol,
            close=event.close,
            volume=event.volume,
            ts=event.timestamp,
        )

        # 2. Update mark-to-market
        self.position_manager.mark_to_market(
            event.symbol,
            event.close,
        )

    # ============================================================
    # SIGNAL
    # ============================================================

    def _handle_signal(self, event: SignalEvent):
        order = self.oms.create_order(event)

        # пока SIM — исполняем сразу
        fill_event = self.oms.simulate_fill(
            order,
            market_price=self.strategy.last_price(event.symbol),
            ts=event.timestamp,
        )

        self._handle_fill(fill_event)
        # 1. Persist signal
        self.storage.log_signal(
            event_id=event.event_id,
            correlation_id=event.correlation_id,
            strategy=event.strategy,
            symbol=event.symbol,
            signal_type=event.signal_type,
            strength=float(event.strength),
            ts=event.timestamp,
        )

        if event.features:
            for name, value in event.features.items():
                self.storage.log_features(
                    event_id=event.event_id,
                    feature_name=name,
                    feature_value=float(value),
                    ts=event.timestamp,
                )

        # 2. Risk check (if exists)
        if self.risk_engine:
            decision = self.risk_engine.pre_trade_check(event)
            if not decision.allowed:
                self.storage.log_risk_event(
                    event_id=event.event_id,
                    symbol=event.symbol,
                    rule_name=decision.rule_name,
                    decision="REJECTED",
                    reason=decision.reason,
                    ts=event.timestamp,
                )
                return

        # 3. Execution
        fill_event = self.execution.execute_signal(event)

        if fill_event:
            self._handle_fill(fill_event)

    # ============================================================
    # FILL
    # ============================================================

    def _handle_fill(self, event: FillEvent):

        # 1. Persist fill
        self.storage.log_fill(
            fill_id=event.fill_id,
            order_id=event.order_id,
            symbol=event.symbol,
            side=event.side,
            qty=event.qty,
            price=event.price,
            commission=event.commission,
            ts=event.timestamp,
        )

        # 2. Accounting update
        position = self.position_manager.update_fill(
            symbol=event.symbol,
            side=event.side,
            qty=event.qty,
            price=event.price,
            commission=event.commission,
            timestamp=event.timestamp,
        )

        self.portfolio_manager.apply_fill(
            side=event.side,
            qty=event.qty,
            price=event.price,
            commission=event.commission,
        )

        state = self.portfolio_manager.compute_state(
            self.position_manager,
            event.timestamp,
        )

        self.storage.log_portfolio_snapshot(
            equity=state.equity,
            cash=state.cash,
            margin_used=state.margin_used,
            exposure=state.exposure,
            drawdown=state.drawdown,
            ts=state.ts,
        )

        # 3. Persist position snapshot
        self.storage.update_position(
            symbol=position.symbol,
            qty=position.qty,
            avg_price=position.avg_price,
            realized_pnl=position.realized_pnl,
            unrealized_pnl=position.unrealized_pnl,
            exposure=position.exposure,
            ts=position.updated_ts,
        )