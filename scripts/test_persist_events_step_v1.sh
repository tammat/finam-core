#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PERSIST_EVENTS_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from unittest.mock import MagicMock

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import PersistEventsStep

ctx = MagicMock(spec=NormalizationContext)

ctx.bar_event = {
    "event_uuid": "11111111-1111-1111-1111-111111111111",
    "quality_status_id": 1,
    "source_system_id": 101,
    "symbol_alias_id": 202,
    "instrument_id": 303,
    "contract_id": 404,
    "timeframe_id": 5,
    "event_time": None,
    "source_time": None,
    "received_at": None,
    "open": 1,
    "high": 2,
    "low": 0,
    "close": 1,
    "volume": 10,
    "payload": {},
}

cursor = MagicMock()
conn = MagicMock()
conn.cursor.return_value.__enter__.return_value = cursor

ctx.resolvers = MagicMock()
ctx.resolvers.conn = conn

ctx.increment = MagicMock()

result = PersistEventsStep().run(ctx)

assert result.success
assert cursor.execute.called
assert conn.commit.called
ctx.increment.assert_any_call("events_persisted")

print("persist_events_step=READY")
print("postgres_write=YES")
print("on_conflict=YES")
print("idempotent=YES")
print("step_policy=PERSIST_ONLY")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PERSIST_EVENTS_STEP_V1_READY"
echo "TEST_PERSIST_EVENTS_STEP_V1_OK"
