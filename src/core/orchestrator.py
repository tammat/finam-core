from core.strategy_stack import StrategyStack
from core.signal_router import SignalRouter
from domain.pipeline_result import PipelineResult


# -------------------------------------------------
# Quantity helpers (support qty and quantity fields)
# -------------------------------------------------

def _get_qty(intent) -> float:
    if hasattr(intent, "qty"):
        return float(getattr(intent, "qty") or 0.0)
    if hasattr(intent, "quantity"):
        return float(getattr(intent, "quantity") or 0.0)
    return 0.0


def _set_qty(intent, new_qty: float):
    """
    Safe quantity update:
    - supports qty
    - supports quantity
    - supports frozen dataclasses (Signal)
    """

    # Mutable qty
    if hasattr(intent, "qty") and not getattr(intent, "__dataclass_fields__", None):
        setattr(intent, "qty", new_qty)
        return intent

    # Mutable quantity
    if hasattr(intent, "quantity") and not getattr(intent, "__dataclass_fields__", None):
        setattr(intent, "quantity", new_qty)
        return intent

    # Frozen dataclass (Signal)
    if getattr(intent, "__dataclass_fields__", None):
        data = intent.__dict__.copy()

        if "qty" in data:
            data["qty"] = new_qty
        elif "quantity" in data:
            data["quantity"] = new_qty

        return intent.__class__(**data)

    return intent


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
            telegram_bot=None,
            regime_detector=None,  # NEW
            regime_sizer=None,  # NEW
            # ← добавили
    ):
        self.position_sizer = position_sizer
        self.regime_detector = regime_detector
        self.regime_sizer = regime_sizer
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

        regime = None
        if self.regime_detector:
            regime = self.regime_detector.detect(event)
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

            # -------------------------------------------------
            # Optional base position sizing
            # -------------------------------------------------
            if self.position_sizer:
                intent2 = self.position_sizer.apply(
                    intent=intent,
                    event=event,
                    portfolio=self.portfolio,
                )
                if intent2 is None:
                    continue
                intent = intent2

            # -------------------------------------------------
            # Optional regime-based sizing
            # -------------------------------------------------
            if self.regime_sizer and regime is not None:
                intent2 = self.regime_sizer.apply(
                    intent=intent,
                    regime=regime,
                    event=event,
                    portfolio=self.portfolio,
                )
                if intent2 is None:
                    continue
                intent = intent2

            # Skip zero-size trades
            # Skip zero-size trades only if quantity field exists
            if hasattr(intent, "qty") or hasattr(intent, "quantity"):
                if _get_qty(intent) <= 0:
                    continue

            context = self.portfolio.build_risk_context()
            risk_result = self.risk_engine.evaluate(intent, context)

            # Case 1: None → reject
            if risk_result is None:
                continue

            # Case 2: RiskDecision-style object
            if hasattr(risk_result, "allowed"):
                if not risk_result.allowed:
                    continue
                # если разрешено — intent не меняем
            else:
                # Case 3: façade returns intent
                intent = risk_result
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
