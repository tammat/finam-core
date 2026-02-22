from datetime import datetime, timezone
import uuid

from storage.postgres import PostgresStorage
from execution.sim_executor import SimExecutionEngine
from execution.oms import OMS
from accounting.position_manager import PositionManager
from accounting.portfolio_manager import PortfolioManager
from risk.risk_engine import RiskEngine
from domain.events import SignalEvent


DSN = "dbname=finam_core user=finam password=finam host=localhost port=5432"


def main():
    storage = PostgresStorage(DSN)
    executor = SimExecutionEngine()
    oms = OMS(storage=storage, execution_engine=executor)

    position_manager = PositionManager()
    portfolio_manager = PortfolioManager(initial_cash=100000.0)
    risk_engine = RiskEngine(position_manager, portfolio_manager)

    # --- 1. Create signal ---
    signal = SignalEvent(
        event_id=str(uuid.uuid4()),
        symbol="TEST",
        signal_type="BUY",
        strength=1.0,
        timestamp=datetime.now(timezone.utc),
        features={"source": "test"}
    )

    storage.log_signal(signal)

    # --- 2. Create order ---
    order = oms.create_order(signal)

    # --- 3. Execute ---
    fills = oms.process_order(
        order,
        market_price=100.0,
        ts=datetime.now(timezone.utc)
    )

    for fill in fills:
        position_manager.on_fill(fill)
        state = portfolio_manager.on_fill(fill)
        risk_engine.evaluate(state)

    print("OK: pipeline executed")


if __name__ == "__main__":
    main()