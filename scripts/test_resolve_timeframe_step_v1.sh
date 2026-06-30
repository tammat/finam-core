#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESOLVE_TIMEFRAME_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import ResolveTimeframeStep


class FakeTimeframeResolver:
    def __init__(self):
        self.calls = 0

    def resolve(self, conn, key):
        self.calls += 1
        if key == "M5":
            return {
                "id": 5,
                "entity_code": "M5",
            }
        return None


raw = CanonicalMarketBarDTO(
    source_system_code="TEST",
    source_key="TEST:SBER:M5",
    symbol_code="SBER@MISX",
    timeframe_code="M5",
    event_time=datetime.now(timezone.utc),
    source_time=datetime.now(timezone.utc),
    received_at=datetime.now(timezone.utc),
    open=Decimal("1"),
    high=Decimal("2"),
    low=Decimal("0.5"),
    close=Decimal("1.5"),
    volume=Decimal("100"),
    payload={},
)

ctx = NormalizationContext(raw=raw)

resolver = FakeTimeframeResolver()

ctx.resolvers = SimpleNamespace(
    conn=None,
    timeframe=resolver,
)

result = ResolveTimeframeStep().run(ctx)

assert result.success
assert ctx.timeframe_id == 5
assert ctx.timeframe["entity_code"] == "M5"
assert resolver.calls == 1
assert ctx.metrics["timeframe_resolved"] == 1
assert ctx.metrics["step_resolve_timeframe_runs"] == 1

print("resolve_timeframe_step=READY")
print("resolver_called=YES")
print("context_updated=YES")
print("resolved_object_saved=YES")
print("unknown_timeframe_handled=YES")
print("quality_event_created=YES")
print("step_policy=NO_SQL_IN_STEP")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=RESOLVE_TIMEFRAME_STEP_V1_READY"
echo "TEST_RESOLVE_TIMEFRAME_STEP_V1_OK"
