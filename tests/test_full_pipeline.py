from core.orchestrator import TradingPipeline


class DummyMarket:
    def get_next_event(self):
        return object()


def test_full_pipeline():
    class DummyStrategy:
        def generate(self, event):
            return None

    class DummyRisk:
        def evaluate(self, intent, context):
            class R:
                allowed = False
            return R()

    class DummyExecution:
        def execute(self, intent):
            return None

    class DummyAccounting:
        def process(self, *args, **kwargs):
            pass

    class DummyStorage:
        def append(self, *args, **kwargs):
            pass

    pipeline = TradingPipeline(
        market_data=DummyMarket(),
        strategy=DummyStrategy(),
        risk_engine=DummyRisk(),
        portfolio=object(),
        execution=DummyExecution(),
        accounting=DummyAccounting(),
        storage=DummyStorage(),
    )

    result = pipeline.run_once()

    assert result.status == "NO_ACTION"
    assert result.order is None