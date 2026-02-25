from core.strategy_stack import StrategyStack
from core.signal_router import SignalRouter
from domain.pipeline_result import PipelineResult


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
            position_sizer=None,
            telegram_bot=None,   # ← добавили
    ):
        self.market_data = market_data
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.portfolio = portfolio
        self.execution = execution
        self.accounting = accounting
        self.storage = storage
        self.telegram_bot = telegram_bot
        # Optional position sizing layer
        self.position_sizer = position_sizer

        # Новый слой (пока не используется тестами)
        # StrategyStack + SignalRouter (production-grade)
        self.signal_router = None


    def run_once(self):

        event = self.market_data.get_next_event()
        if event is None:
            return PipelineResult(status="NO_ACTION", order=None)

        intents = self.strategy.generate(event)

        if intents is None:
            return PipelineResult(status="NO_ACTION", order=None)

        if not isinstance(intents, list):
            intents = [intents]

        if not intents:
            return PipelineResult(status="NO_ACTION", order=None)

        if self.signal_router:
            intents = self.signal_router.route(intents)
            if not intents:
                return PipelineResult(status="NO_ACTION", order=None)

        for intent in intents:

            context = self.portfolio.build_risk_context()
            risk_result = self.risk_engine.evaluate(intent, context)

            if not getattr(risk_result, "allowed", False):
                continue

            if hasattr(self.execution, "place"):
                execution_result = self.execution.place(intent)
            else:
                execution_result = self.execution.execute(intent)

            if execution_result is None:
                continue

            self.accounting.apply(execution_result)

            if self.storage:
                self.storage.append(execution_result)

            return PipelineResult(
                status="ORDER_EXECUTED",
                order=execution_result,
            )

        return PipelineResult(status="NO_ACTION", order=None)
