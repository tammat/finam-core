# tests/test_sim_pipeline.py

from execution.execution_engine import ExecutionEngine
from src.infra.brokers.sim_broker import SimBrokerAdapter
from storage.postgres_storage import PostgresStorage
from src.core.events.fill_event import FillEvent
DSN = "postgresql://test:test@localhost:5432/test_db"


def test_full_sim_pipeline():
    from storage.sqlite_storage import SQLiteStorage

    storage = SQLiteStorage(":memory:")
    broker = SimBrokerAdapter()
    executor = ExecutionEngine(broker=broker)

    signal = {
        "symbol": "TEST",
        "side": "BUY",
        "quantity": 1,
    }

    result = executor.execute_signal(
        account_id="SIM",
        signal=signal,
    )

    assert isinstance(result, FillEvent)
    assert result.symbol == "TEST"
    assert result.side == "BUY"
    assert result.qty == 1