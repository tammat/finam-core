#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export ENABLE_REAL_EXECUTION_SAFETY_GATE=0

python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine

events = []

class FakeJournal:
    def log_execution_event(self, **kwargs):
        events.append(kwargs)

class FakeOrdersClient:
    def place_market_order(self, **kwargs):
        return {"status": "ACCEPTED", "order_id": "ord1", **kwargs}

engine = RealExecutionEngine(FakeOrdersClient())
engine.execution_journal = FakeJournal()

res = engine.execute(
    intent={"symbol": "SBER@MISX", "side": "BUY", "qty": 1, "price": 300},
    market_state={"last": 300},
)

assert res.status == "ACCEPTED", res
assert events, events
assert events[-1]["event_type"] == "REAL_EXECUTION_RESULT", events
assert events[-1]["symbol"] == "SBER@MISX", events
assert events[-1]["status"] == "ACCEPTED", events

print("OK: RealExecutionEngine execution journal mock")
PY
