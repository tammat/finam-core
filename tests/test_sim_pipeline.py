import uuid
from datetime import datetime, timezone

from storage.postgres import PostgresStorage
from execution.sim_executor import SimExecutionEngine
from execution.oms import OMS
from accounting.position_manager import PositionManager
from accounting.portfolio_manager import PortfolioManager
from risk.risk_engine import RiskEngine
from core.events import SignalEvent


DSN = "dbname=finam_core user=finam password=finam host=localhost port=5432"


def test_full_sim_pipeline():
    storage = PostgresStorage(DSN)
    executor = SimExecutionEngine()
    oms = OMS(storage=storage, execution_engine=executor)

    position_manager = PositionManager()
    portfolio_manager = PortfolioManager(initial_cash=100000.0)
    risk_engine = RiskEngine(position_manager, portfolio_manager)

    signal = SignalEvent(
        event_id=str(uuid.uuid4()),
        symbol="TEST",
        signal_type="BUY",
        strength=1.0,
        timestamp=datetime.now(timezone.utc),
        features=None
    )

    storage.log_signal(signal)
    order = oms.create_order(signal)

    fills = oms.process_order(order, 100.0, datetime.now(timezone.utc))

    assert len(fills) > 0

    for fill in fills:
        position_manager.on_fill(fill)
        state = portfolio_manager.on_fill(fill)
        risk_engine.evaluate(state)

    assert state.equity >= 0