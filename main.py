import sys
from pathlib import Path

SDK_PATH = Path(__file__).parent / "infra" / "finam" / "sdk"
sys.path.append(str(SDK_PATH))
from core.event_bus import EventBus
from core.engine import Engine
from data.market_data import DummyMarketData
from strategy.momentum import MomentumStrategy
from portfolio.portfolio import Portfolio
from risk.risk_engine import RiskEngine
from execution.execution_engine import SimExecutionEngine
from storage.postgres import PostgresStorage
from ai.ml_strategy import MLStrategy

def main():
    event_bus = EventBus()

    storage = PostgresStorage()

    data = DummyMarketData(event_bus)
    strategy = MomentumStrategy(event_bus)
    ml_strategy = MLStrategy(event_bus)
    portfolio = Portfolio()
    risk = RiskEngine(portfolio, event_bus, storage.last_price)
    execution = SimExecutionEngine(event_bus, storage.last_price)

    engine = Engine(
        data=data,
        strategies=[strategy, ml_strategy],
        risk=risk,
        execution=execution,
        portfolio=portfolio,
        storage=storage,
    )
    processed = engine.run()

    print("Processed events:", processed)
    print("Positions:", portfolio.positions)

    return 0


if __name__ == "__main__":
    main()