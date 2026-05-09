#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"
export EXECUTION_MODE=real_dry_run

python - <<'PY'
from finam_core.execution.execution_dispatcher import ExecutionDispatcher


class FakeRealExecutionEngine:
    def __init__(self):
        self.calls = 0

    def execute(self, intent, market_state=None):
        self.calls += 1
        return {
            "status": "SENT",
            "order_id": "broker_fake_001",
            "client_order_id": intent.get("client_order_id"),
        }


engine = FakeRealExecutionEngine()
dispatcher = ExecutionDispatcher(real_execution_engine=engine)

intent = {
    "symbol": "NGH6@RTSX",
    "side": "BUY",
    "qty": 1.0,
    "price": 100.0,
    "strategy": "dispatcher_oms_test",
    "ts": "20260509T1300",
}

r1 = dispatcher.execute(dict(intent), {})
r2 = dispatcher.execute(dict(intent), {})

assert r1["status"] == "SENT", r1
assert r2["status"] == "REJECTED", r2
assert r2["reason"] == "duplicate_client_order_id", r2
assert engine.calls == 1, engine.calls

print("EXECUTION_DISPATCHER_OMS_GUARD_OK")
PY
