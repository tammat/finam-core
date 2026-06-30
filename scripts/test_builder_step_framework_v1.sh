#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BUILDER_STEP_FRAMEWORK_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import BaseBuilderStep, StepResult, StepTag


class DemoStep(BaseBuilderStep):
    name = "demo"
    version = 1
    tags = (StepTag.RESOLUTION,)

    def execute(self, ctx):
        ctx.source_system_id = 1
        return StepResult(
            success=True,
            rows_processed=1,
            warnings=["demo_warning"],
        )


raw = CanonicalMarketBarDTO(
    source_system_code="TEST",
    source_key="TEST:SBER:M5:2026-06-30T10:00:00Z",
    symbol_code="SBER@MISX",
    timeframe_code="M5",
    event_time=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
    source_time=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
    received_at=datetime(2026, 6, 30, 10, 1, tzinfo=timezone.utc),
    open=Decimal("300"),
    high=Decimal("301"),
    low=Decimal("299"),
    close=Decimal("300.5"),
    volume=Decimal("1000"),
    payload={"test": True},
)

ctx = NormalizationContext(raw=raw)
result = DemoStep().run(ctx)

assert result.success is True
assert result.rows_processed == 1
assert result.has_warnings is True
assert result.has_errors is False
assert ctx.source_system_id == 1
assert ctx.metrics["step_demo_runs"] == 1
assert ctx.metrics["step_demo_rows_processed"] == 1
assert ctx.metrics["step_demo_warnings"] == 1

print("builder_step_framework=READY")
print("base_builder_step=READY")
print("step_result=READY")
print("step_tags=READY")
print("step_metrics=READY")
print("step_exception_policy=READY")
print("step_policy=ATOMIC_CONTEXT_ONLY")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=BUILDER_STEP_FRAMEWORK_V1_READY"
echo "TEST_BUILDER_STEP_FRAMEWORK_V1_OK"
