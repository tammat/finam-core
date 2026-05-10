#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"
export EXECUTION_MODE=real
export FUTURES_REAL_ALLOWED_FROM=2026-01-01
export ENABLE_REAL_FUTURES_TRADING=1
export FUTURES_MAX_MARGIN_UTILIZATION=0.50
export FUTURES_MARGIN_BRM6=25000

python - <<'PY'
from finam_core.execution.execution_dispatcher import ExecutionDispatcher


class FakeRealExecutionEngine:
    def __init__(self):
        self.calls = 0

    def execute(self, intent, market_state=None):
        self.calls += 1
        return {"status": "SENT", "order_id": "broker_should_not_be_called"}


engine = FakeRealExecutionEngine()
dispatcher = ExecutionDispatcher(real_execution_engine=engine)

result = dispatcher.execute(
    {
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 3.0,
        "price": 100.0,
        "strategy": "futures_margin_guard_test",
        "ts": "20260510T1100",
    },
    {
        "portfolio_equity": 200000.0,
        "used_margin": 50000.0,
    },
)

assert result["status"] == "REJECTED", result
assert result["reason"] == "futures_margin_utilization_limit", result
assert engine.calls == 0, engine.calls

print("EXECUTION_DISPATCHER_FUTURES_MARGIN_GUARD_OK")
PY
