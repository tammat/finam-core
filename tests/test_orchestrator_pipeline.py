import pytest

from core.orchestrator import TradingPipeline


class DummyEvent:
    pass


class DummyMarket:
    def get_next_event(self):
        return DummyEvent()


class DummyStrategy:
    def generate(self, event):
        # single intent
        return {"symbol": "SI"}


class DummyMultiStrategy:
    def generate(self, event):
        # multiple intents
        return [{"id": 1}, {"id": 2}]


class DummyRiskAllow:
    def evaluate(self, intent, context):
        class R:
            allowed = True
        return R()


class DummyRiskSelective:
    def evaluate(self, intent, context):
        class R:
            allowed = isinstance(intent, dict) and intent.get("id") == 2
        return R()


class DummyRiskBlockAll:
    def evaluate(self, intent, context):
        class R:
            allowed = False
        return R()


class DummyExecution:
    def place(self, intent):
        return {"filled": True}


class DummyPortfolio:
    def build_risk_context(self):
        return {}


class DummyAccounting:
    def apply(self, execution_result):
        pass


class DummyStorage:
    def append(self, execution_result):
        pass


class DummyRouter:
    def route(self, intents):
        # drop first intent
        return intents[1:]


def build_pipeline(strategy, risk):
    return TradingPipeline(
        market_data=DummyMarket(),
        strategy=strategy,
        risk_engine=risk,
        portfolio=DummyPortfolio(),
        execution=DummyExecution(),
        accounting=DummyAccounting(),
        storage=DummyStorage(),
    )


def test_order_executed_single_intent():
    pipeline = build_pipeline(DummyStrategy(), DummyRiskAllow())
    result = pipeline.run_once()
    assert result.status == "ORDER_EXECUTED"


def test_no_action_when_risk_blocks():
    pipeline = build_pipeline(DummyStrategy(), DummyRiskBlockAll())
    result = pipeline.run_once()
    assert result.status == "NO_ACTION"


def test_first_valid_intent_wins():
    pipeline = build_pipeline(DummyMultiStrategy(), DummyRiskSelective())
    result = pipeline.run_once()
    assert result.status == "ORDER_EXECUTED"


def test_signal_router_applied():
    pipeline = build_pipeline(DummyMultiStrategy(), DummyRiskAllow())
    pipeline.signal_router = DummyRouter()
    result = pipeline.run_once()
    assert result.status == "ORDER_EXECUTED"