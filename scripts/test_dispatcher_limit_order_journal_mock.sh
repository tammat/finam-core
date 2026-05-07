#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real
export REAL_EXECUTION_ENABLED=0
export REAL_ORDER_CONFIRM=0

python - <<'PY'
from finam_core.execution.execution_dispatcher import ExecutionDispatcher

events = []

class FakeJournal:
    def log_execution_event(self, **kwargs):
        events.append(kwargs)

class FakeOrdersClient:
    def place_limit_order(self, **kwargs):
        return {
            "status": "DRY_RUN_ACCEPTED",
            "reason": "real_order_confirm_disabled",
            "order_id": "dry1",
            **kwargs,
        }

dispatcher = ExecutionDispatcher(
    orders_client=FakeOrdersClient(),
    real_execution_engine=None,
    logger=FakeJournal(),
)

res = dispatcher.place_limit_order(
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1,
    limit_price=70.0,
)

assert res["status"] == "DRY_RUN_ACCEPTED", res
assert events, events
assert events[-1]["event_type"] == "LIMIT_ORDER_RESULT", events
assert events[-1]["symbol"] == "BRM6@RTSX", events
assert events[-1]["status"] == "DRY_RUN_ACCEPTED", events
assert events[-1]["order_id"] == "dry1", events

print("OK: dispatcher limit order journal mock")
PY
