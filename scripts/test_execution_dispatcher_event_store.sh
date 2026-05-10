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
from finam_core.events.event_store import EventStore
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch


class FakeRealExecutionEngine:
    def __init__(self):
        self.calls = 0

    def execute(self, intent, market_state=None):
        self.calls += 1
        return {
            "status": "SENT",
            "order_id": "broker_event_store_001",
            "client_order_id": intent.get("client_order_id"),
        }


ks = PersistentKillSwitch()
ks.ensure_schema()
ks.deactivate(scope="GLOBAL", reason="event_store_test_clear", source="test")
ks.deactivate(scope="SYMBOL", symbol="NGH6@RTSX", reason="event_store_test_clear", source="test")

engine = FakeRealExecutionEngine()
dispatcher = ExecutionDispatcher(real_execution_engine=engine)

intent = {
    "symbol": "NGH6@RTSX",
    "side": "BUY",
    "qty": 1.0,
    "price": 100.0,
    "strategy": "event_store_dispatcher_test",
    "ts": str(time.time_ns()),
}

result = dispatcher.execute(
    dict(intent),
    {
        "portfolio_equity": 200000.0,
        "used_margin": 0.0,
    },
)

assert result["status"] == "SENT", result
assert engine.calls == 1, engine.calls

store = EventStore()
events = store.list_by_aggregate(
    aggregate_type="order",
    aggregate_id=result["client_order_id"],
)

event_types = [e.event_type for e in events]

assert "ORDER_CREATED" in event_types, event_types
assert "ORDER_DISPATCH_RESULT" in event_types, event_types

print("EXECUTION_DISPATCHER_EVENT_STORE_OK", result["client_order_id"])
PY
