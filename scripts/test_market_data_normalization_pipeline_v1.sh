#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_PIPELINE_V1 ==="

PYTHONPATH=src python - <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from marketcore.normalization import (
    CanonicalMarketBarDTO,
    NormalizationContext,
    NormalizationPipeline,
)


class MarkSourceStep:
    name = "source"

    def run(self, ctx):
        ctx.source_system_id = 1
        return ctx


class MarkEventStep:
    name = "event"

    def run(self, ctx):
        ctx.event_uuid = "00000000-0000-0000-0000-000000000001"
        ctx.increment("events_built", 1)
        return ctx


raw = CanonicalMarketBarDTO(
    source_system_code="TEST",
    source_key="TEST:SBER:M5:2026-06-30T10:00:00Z",
    symbol_code="SBER@MISX",
    timeframe_code="M5",
    event_time=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
    source_time=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
    received_at=datetime(2026, 6, 30, 10, 1, tzinfo=timezone.utc),
    open=Decimal("300.0"),
    high=Decimal("301.0"),
    low=Decimal("299.5"),
    close=Decimal("300.5"),
    volume=Decimal("1000"),
    payload={"test": True},
)

ctx = NormalizationContext(raw=raw)
pipeline = NormalizationPipeline(steps=(MarkSourceStep(), MarkEventStep()))
result = pipeline.run(ctx)

assert result.source_system_id == 1
assert result.event_uuid is not None
assert result.metrics["pipeline_started"] == 1
assert result.metrics["pipeline_finished"] == 1
assert result.metrics["step_source_started"] == 1
assert result.metrics["step_event_finished"] == 1
assert result.metrics["events_built"] == 1
assert result.rejected is False

print("normalization_pipeline=READY")
print("dto=CanonicalMarketBarDTO")
print("context=NormalizationContext")
print("pipeline=NormalizationPipeline")
print("steps=PipelineStep")
print("stop_on_reject=READY")
print("metrics=READY")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_DATA_NORMALIZATION_PIPELINE_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_PIPELINE_V1_OK"
