#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"
export EXECUTION_MODE=real
export FUTURES_REAL_ALLOWED_FROM=2026-01-01
export ENABLE_REAL_FUTURES_TRADING=1
export FUTURES_MAX_MARGIN_UTILIZATION=0.90
export FUTURES_MARGIN_NGH6=5000

python - <<'PY'
import time

from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch


class FakeRealExecutionEngine:
    def __init__(self):
        self.calls = 0

    def execute(self, intent, market_state=None):
        self.calls += 1
        return {"status": "SENT", "order_id": "broker_should_not_be_called"}


ks = PersistentKillSwitch()
ks.ensure_schema()
ks.activate(scope="GLOBAL", reason="test_global_freeze", source="test")

engine = FakeRealExecutionEngine()
dispatcher = ExecutionDispatcher(real_execution_engine=engine)

result = dispatcher.execute(
    {
        "symbol": "NGH6@RTSX",
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
        "strategy": "persistent_kill_switch_test",
        "ts": str(time.time_ns()),
    },
    {
        "portfolio_equity": 200000.0,
        "used_margin": 0.0,
    },
)

assert result["status"] == "REJECTED", result
assert result["reason"] == "persistent_kill_switch_active", result
assert result["kill_switch_reason"] == "test_global_freeze", result
assert engine.calls == 0, engine.calls

ks.deactivate(scope="GLOBAL", reason="test_clear", source="test")

print("EXECUTION_DISPATCHER_PERSISTENT_KILL_SWITCH_OK")
PY
