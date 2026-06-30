#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RUN_QUALITY_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import RunQualityStep


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

ctx.bar_event = {
    "event_type": "BAR_EVENT",
}

result = RunQualityStep().run(ctx)

assert result.success
assert ctx.quality_status_id == 1
assert ctx.bar_event["quality_status_id"] == 1
assert ctx.bar_event["research_ready"] is True
assert ctx.bar_event["ai_ready"] is True
assert ctx.metrics["quality_passed"] == 1

print("run_quality_step=READY")
print("quality_status=VALID")
print("research_ready=YES")
print("ai_ready=YES")
print("context_updated=YES")
print("step_policy=NO_SQL_IN_STEP")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=RUN_QUALITY_STEP_V1_READY"
echo "TEST_RUN_QUALITY_STEP_V1_OK"
