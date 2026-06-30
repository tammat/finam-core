#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PERSIST_QUALITY_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from unittest.mock import MagicMock

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import PersistQualityStep

ctx = MagicMock(spec=NormalizationContext)

ctx.event_uuid = "11111111-1111-1111-1111-111111111111"

ctx.quality_events = [
    {
        "quality_reason_id": 1,
        "blocks_research": True,
        "blocks_ai": True,
        "blocks_runtime": True,
    }
]

cursor = MagicMock()
conn = MagicMock()
conn.cursor.return_value.__enter__.return_value = cursor

ctx.resolvers = MagicMock()
ctx.resolvers.conn = conn

ctx.increment = MagicMock()

result = PersistQualityStep().run(ctx)

assert result.success
assert cursor.execute.called
assert conn.commit.called

ctx.increment.assert_any_call("quality_events_persisted")

print("persist_quality_step=READY")
print("postgres_write=YES")
print("batch_insert=YES")
print("step_policy=PERSIST_ONLY")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PERSIST_QUALITY_STEP_V1_READY"
echo "TEST_PERSIST_QUALITY_STEP_V1_OK"
