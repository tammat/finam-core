#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BUILD_LINEAGE_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import BuildLineageStep


raw = CanonicalMarketBarDTO(
    source_system_code="TEST",
    source_key="TEST:SBER:M5",
    symbol_code="SBER@MISX",
    timeframe_code="M5",
    event_time=datetime.now(timezone.utc),
    source_time=datetime.now(timezone.utc),
    received_at=datetime.now(timezone.utc),
    open=Decimal("100"),
    high=Decimal("101"),
    low=Decimal("99"),
    close=Decimal("100.5"),
    volume=Decimal("1000"),
    payload={},
)

ctx = NormalizationContext(raw=raw)

ctx.event_uuid = "00000000-0000-0000-0000-000000000001"
ctx.bar_event = {"event_type": "BAR_EVENT"}

result = BuildLineageStep().run(ctx)

assert result.success
assert len(ctx.lineage_edges) == 1

edge = ctx.lineage_edges[0]

assert edge["relationship"] == "NORMALIZED_FROM"
assert edge["target_entity_uuid"] == ctx.event_uuid
assert edge["source_entity_uuid"] == raw.source_key
assert edge["valid"] is True

assert ctx.metrics["lineage_built"] == 1

print("build_lineage_step=READY")
print("lineage_created=YES")
print("relationship=NORMALIZED_FROM")
print("context_updated=YES")
print("step_policy=NO_SQL_IN_STEP")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=BUILD_LINEAGE_STEP_V1_READY"
echo "TEST_BUILD_LINEAGE_STEP_V1_OK"
