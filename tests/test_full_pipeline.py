from core.orchestrator import TradingPipeline


class Dummy:
    def get_latest(self): return "DATA"
    def generate_signal(self, data): return "SIGNAL"
    def evaluate(self, signal, portfolio): return signal
    def execute(self, signal): return "ORDER"
    def process(self, order): pass
    def update(self, order): pass
    def persist(self, order): pass


def test_full_pipeline():
    pipeline = TradingPipeline(
        market_data=Dummy(),
        strategy=Dummy(),
        risk_engine=Dummy(),
        portfolio=Dummy(),
        execution=Dummy(),
        accounting=Dummy(),
        storage=Dummy(),
    )

    result = pipeline.run_once()

    assert result.status == "ORDER_EXECUTED"
    assert result.order == "ORDER"