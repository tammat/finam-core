#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real_dry_run
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export BROKER_CATEGORY=KSUR
export ENABLE_REAL_EXECUTION_SAFETY_GATE=0

python -m py_compile \
  src/finam_core/execution/execution_dispatcher.py \
  src/finam_core/execution/fill_persistence_service.py \
  src/finam_core/execution/fill_metadata_factory.py

python - <<'PY'
import uuid

from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.execution.real_execution import RealOrderResult


class MockKillSwitch:
    def is_active(self, symbol=None):
        return False


class MockFuturesGate:
    def check(self, symbol=None, execution_mode=None):
        class Decision:
            allowed = True
            reason = "разрешено"
        return Decision()


class MockMarginGate:
    def check(self, **kwargs):
        class Decision:
            allowed = True
            reason = "разрешено"
            required_margin = 0.0
            margin_utilization_after = 0.0
        return Decision()


class MockRealExecution:
    def execute(self, intent=None, market_state=None):
        return RealOrderResult(
            symbol=intent["symbol"],
            side=intent["side"],
            qty=float(intent["qty"]),
            price=float(intent.get("price") or 0.0),
            status="DRY_RUN_ACCEPTED",
            order_id="mock-real-order-001",
            reason="тестовый dry-run",
            raw={"mock": True},
        )


class MockPersistence:
    def __init__(self):
        self.fill = None
        self.execution_type = None

    def persist_fill(self, fill, execution_type="paper"):
        self.fill = fill
        self.execution_type = execution_type
        return {
            "fill_logged": True,
            "signal_linked": True,
            "fill_id": getattr(fill, "fill_id", None),
            "signal_id": getattr(fill, "signal_id", None),
        }


persistence = MockPersistence()
dispatcher = ExecutionDispatcher(
    real_execution_engine=MockRealExecution(),
    fill_persistence_service=persistence,
)

dispatcher._persistent_kill_switch = MockKillSwitch()
dispatcher._futures_access_gate = MockFuturesGate()
dispatcher._futures_margin_guard = MockMarginGate()

intent = {
    "client_order_id": f"test-real-persist-{uuid.uuid4().hex}",
    "symbol": "SBER@MISX",
    "side": "BUY",
    "qty": 1,
    "price": 300,
    "signal_id": "sig-real-persist-001",
    "strategy": "REAL_PERSISTENCE_TEST",
    "horizon": "INTRADAY",
    "timeframe": "M5",
}

market_state = {"regime": "trend_high_vol"}

result = dispatcher.execute(intent=intent, market_state=market_state)

assert result.status == "DRY_RUN_ACCEPTED", result
assert result.signal_id == "sig-real-persist-001", result
assert result.payload["strategy"] == "REAL_PERSISTENCE_TEST", result.payload

assert persistence.fill is result
assert persistence.execution_type == "real_dry_run"

print("OK: REAL/DRY_RUN результат сохраняется через FillPersistenceService")
PY
