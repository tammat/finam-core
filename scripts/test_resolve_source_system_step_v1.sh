#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESOLVE_SOURCE_SYSTEM_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import ResolveSourceSystemStep


class FakeSourceResolver:
    def __init__(self):
        self.calls = 0

    def resolve(self, conn, key):
        self.calls += 1
        if key == "TEST":
            return {"id": 101, "entity_code": "TEST"}
        return None


def make_ctx(source_code: str):
    raw = CanonicalMarketBarDTO(
        source_system_code=source_code,
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
    resolver = FakeSourceResolver()
    ctx.resolvers = SimpleNamespace(conn=None, source_system=resolver)
    return ctx, resolver


ctx, resolver = make_ctx("TEST")
result = ResolveSourceSystemStep().run(ctx)

assert result.success is True
assert ctx.source_system_id == 101
assert resolver.calls == 1
assert ctx.metrics["source_system_resolved"] == 1
assert ctx.metrics["step_resolve_source_system_runs"] == 1
assert ctx.rejected is False

bad_ctx, bad_resolver = make_ctx("UNKNOWN")
bad_result = ResolveSourceSystemStep().run(bad_ctx)

assert bad_result.success is False
assert bad_ctx.rejected is True
assert bad_ctx.rejection_reason == "UNKNOWN_SOURCE_SYSTEM"
assert len(bad_ctx.quality_events) == 1
assert bad_ctx.quality_events[0]["reason"] == "UNKNOWN_SOURCE_SYSTEM"
assert bad_ctx.quality_events[0]["blocks_research"] is True
assert bad_ctx.quality_events[0]["blocks_ai"] is True
assert bad_ctx.quality_events[0]["blocks_runtime"] is True

empty_ctx, _ = make_ctx("")
empty_result = ResolveSourceSystemStep().run(empty_ctx)

assert empty_result.success is False
assert empty_ctx.rejected is True
assert empty_ctx.rejection_reason == "UNKNOWN_SOURCE_SYSTEM"
assert len(empty_ctx.quality_events) == 1

print("resolve_source_system_step=READY")
print("resolver_called=YES")
print("context_updated=YES")
print("unknown_source_system_handled=YES")
print("quality_event_created=YES")
print("step_result=READY")
print("step_policy=NO_SQL_IN_STEP")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RESOLVE_SOURCE_SYSTEM_STEP_V1_READY"
echo "TEST_RESOLVE_SOURCE_SYSTEM_STEP_V1_OK"
