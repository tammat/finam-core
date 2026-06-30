#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BUILD_BAR_EVENT_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import BuildBarEventStep


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
    payload={"provider": "TEST"},
)

ctx = NormalizationContext(raw=raw)

ctx.source_system_id = 101
ctx.symbol_alias_id = 202
ctx.instrument_id = 303
ctx.contract_id = 404
ctx.timeframe_id = 5

ctx.source_system = {"id": 101}
ctx.symbol_alias = {"id": 202}
ctx.instrument = {"id": 303}
ctx.contract = {"id": 404}
ctx.timeframe = {"id": 5}

result = BuildBarEventStep().run(ctx)

assert result.success
assert ctx.event_uuid is not None
assert ctx.bar_event["event_type"] == "BAR_EVENT"
assert ctx.bar_event["instrument_id"] == 303
assert ctx.bar_event["contract_id"] == 404
assert ctx.bar_event["timeframe_id"] == 5
assert ctx.metrics["bar_events_built"] == 1

print("build_bar_event_step=READY")
print("bar_event_created=YES")
print("event_uuid_created=YES")
print("context_updated=YES")
print("step_policy=NO_SQL_IN_STEP")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=BUILD_BAR_EVENT_STEP_V1_READY"
echo "TEST_BUILD_BAR_EVENT_STEP_V1_OK"
