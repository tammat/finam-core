from core.strategy_manager import StrategyManager


class PipelineResult:
    def __init__(self, status="NO_ACTION", order=None):
        self.status = status
        self.order = order


class TradingPipeline:

    def __init__(
            self,
            market_data=None,
            strategy=None,
            risk_engine=None,
            portfolio=None,
            execution=None,
            accounting=None,
            storage=None,
            position_sizer=None,  # ← добавили
    ):
        self.market_data = market_data
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.portfolio = portfolio
        self.execution = execution
        self.accounting = accounting
        self.storage = storage
        # Optional position sizing layer
        self.position_sizer = position_sizer

        # Новый слой (пока не используется тестами)
        self.strategy_manager = StrategyManager()
        if strategy:
            self.strategy_manager.register(strategy)

    def run_once(self):
        """
        Legacy full pipeline flow expected by tests.
        """

        # 1️⃣ Market data
        data = None
        if self.market_data and hasattr(self.market_data, "get_latest"):
            data = self.market_data.get_latest()

        # 2️⃣ Strategy
        signal = None
        if self.strategy and hasattr(self.strategy, "generate_signal"):
            signal = self.strategy.generate_signal(data)

        if not signal:
            return PipelineResult()

        # 3️⃣ Risk
        approved = signal
        if self.risk_engine and hasattr(self.risk_engine, "evaluate"):
            approved = self.risk_engine.evaluate(signal, self.portfolio)

        if not approved:
            return PipelineResult()

        # 4️⃣ Execution
        order = None

        if self.execution and hasattr(self.execution, "execute"):

            # ---------------- Position Sizing (Immutable) ----------------
            execution_signal = approved

            if (
                self.position_sizer is not None
                and self.portfolio is not None
                and hasattr(self.portfolio, "build_context")
            ):
                try:
                    context = self.portfolio.build_context()
                    sizing_result = self.position_sizer.size(approved, context)

                    if hasattr(sizing_result, "size") and sizing_result.size is not None:
                        # Create shallow copy of signal to avoid mutation
                        if hasattr(approved, "__dict__"):
                            execution_signal = approved.__class__(**approved.__dict__)
                            if hasattr(execution_signal, "qty"):
                                execution_signal.qty = sizing_result.size
                except Exception:
                    execution_signal = approved  # fail-safe fallback

            order = self.execution.execute(execution_signal)
        # 5️⃣ Accounting
        if self.accounting and hasattr(self.accounting, "process"):
            self.accounting.process(order)

        # 6️⃣ Portfolio
        if self.portfolio and hasattr(self.portfolio, "update"):
            self.portfolio.update(order)

        # 7️⃣ Storage
        if self.storage and hasattr(self.storage, "persist"):
            self.storage.persist(order)

        return PipelineResult(
            status="ORDER_EXECUTED",
            order=order,
        )