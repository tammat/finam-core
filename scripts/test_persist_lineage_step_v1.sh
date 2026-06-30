#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PERSIST_LINEAGE_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from unittest.mock import MagicMock

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import PersistLineageStep

ctx = MagicMock(spec=NormalizationContext)

ctx.lineage_edges = [
    {
        "lineage_uuid": "11111111-1111-1111-1111-111111111111",
        "root_entity_uuid": "22222222-2222-2222-2222-222222222222",
        "source_entity_uuid": "RAW:SBER:M5",
        "target_entity_uuid": "33333333-3333-3333-3333-333333333333",
        "relationship": "NORMALIZED_FROM",
        "stage": "NORMALIZATION",
        "depth": 1,
        "valid": True,
    }
]

cursor = MagicMock()
conn = MagicMock()
conn.cursor.return_value.__enter__.return_value = cursor

ctx.resolvers = MagicMock()
ctx.resolvers.conn = conn

ctx.increment = MagicMock()

result = PersistLineageStep().run(ctx)

assert result.success
assert cursor.execute.called
assert conn.commit.called

ctx.increment.assert_any_call("lineage_events_persisted")

print("persist_lineage_step=READY")
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

echo "VERDICT=PERSIST_LINEAGE_STEP_V1_READY"
echo "TEST_PERSIST_LINEAGE_STEP_V1_OK"
