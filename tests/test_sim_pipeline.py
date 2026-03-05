"""tests/test_sim_pipeline.py

Minimal end-to-end simulation smoke:
ExecutionEngine(broker=SimBrokerAdapter) should return core FillEvent.

Keep this test deterministic and free of side effects (no top-level prints).
"""

from finam_core.execution.execution_engine import ExecutionEngine
from finam_core.infra.brokers.sim_broker import SimBrokerAdapter
from finam_core.core.events.fill_event import FillEvent


def test_full_sim_pipeline():
    # NOTE: storage is intentionally unused here; the executor path should not
    # require persistence for a single simulated fill.
    from finam_core.storage.sqlite_storage import SQLiteStorage

    _storage = SQLiteStorage(":memory:")

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

    # Type contract
    assert isinstance(result, FillEvent)

    # Payload contract (tolerant to minor naming differences)
    assert getattr(result, "symbol", None) == "TEST"
    assert str(getattr(result, "side", "")).upper() == "BUY"
    assert float(getattr(result, "qty", getattr(result, "quantity", 0))) == 1.0