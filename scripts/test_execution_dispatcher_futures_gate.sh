#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"
export EXECUTION_MODE=real
export FUTURES_REAL_ALLOWED_FROM=2026-07-01
export ENABLE_REAL_FUTURES_TRADING=0

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
        "qty": 1.0,
        "price": 100.0,
        "strategy": "futures_gate_test",
        "ts": "20260510T1000",
    },
    {},
)

assert result["status"] == "REJECTED", result
assert "futures_real_trading_blocked_until_2026-07-01" in result["reason"], result
assert engine.calls == 0, engine.calls

print("EXECUTION_DISPATCHER_FUTURES_GATE_OK")
PY
