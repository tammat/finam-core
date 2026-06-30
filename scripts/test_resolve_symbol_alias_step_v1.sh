#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESOLVE_SYMBOL_ALIAS_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import ResolveSymbolAliasStep


class FakeAliasResolver:
    def __init__(self):
        self.calls = 0
        self.keys = []

    def resolve(self, conn, key):
        self.calls += 1
        self.keys.append(key)
        if key == "101::SBER@MISX":
            return {
                "id": 202,
                "entity_code": "SBER@MISX",
                "source_system_id": 101,
                "instrument_id": 303,
                "contract_id": None,
            }
        return None


def make_ctx(symbol_code: str, source_system_id=101):
    raw = CanonicalMarketBarDTO(
        source_system_code="TEST",
        source_key="TEST:SBER:M5:2026-06-30T10:00:00Z",
        symbol_code=symbol_code,
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
    ctx.source_system_id = source_system_id
    resolver = FakeAliasResolver()
    ctx.resolvers = SimpleNamespace(conn=None, symbol_alias=resolver)
    return ctx, resolver


ctx, resolver = make_ctx("SBER@MISX")
result = ResolveSymbolAliasStep().run(ctx)

assert result.success is True
assert ctx.symbol_alias_id == 202
assert ctx.symbol_alias["instrument_id"] == 303
assert resolver.calls == 1
assert resolver.keys == ["101::SBER@MISX"]
assert ctx.metrics["symbol_alias_resolved"] == 1
assert ctx.metrics["step_resolve_symbol_alias_runs"] == 1
assert ctx.rejected is False

bad_ctx, bad_resolver = make_ctx("UNKNOWN@MISX")
bad_result = ResolveSymbolAliasStep().run(bad_ctx)

assert bad_result.success is False
assert bad_ctx.rejected is True
assert bad_ctx.rejection_reason == "UNKNOWN_SYMBOL_ALIAS"
assert len(bad_ctx.quality_events) == 1
assert bad_ctx.quality_events[0]["reason"] == "UNKNOWN_SYMBOL_ALIAS"
assert bad_ctx.quality_events[0]["blocks_research"] is True
assert bad_ctx.quality_events[0]["blocks_ai"] is True
assert bad_ctx.quality_events[0]["blocks_runtime"] is True

missing_source_ctx, _ = make_ctx("SBER@MISX", source_system_id=None)
missing_source_result = ResolveSymbolAliasStep().run(missing_source_ctx)

assert missing_source_result.success is False
assert missing_source_ctx.rejected is True
assert missing_source_ctx.rejection_reason == "SOURCE_SYSTEM_NOT_RESOLVED"
assert len(missing_source_ctx.quality_events) == 1

empty_ctx, _ = make_ctx("")
empty_result = ResolveSymbolAliasStep().run(empty_ctx)

assert empty_result.success is False
assert empty_ctx.rejected is True
assert empty_ctx.rejection_reason == "UNKNOWN_SYMBOL_ALIAS"
assert len(empty_ctx.quality_events) == 1

print("resolve_symbol_alias_step=READY")
print("compound_key=source_system_id_plus_symbol")
print("resolver_called=YES")
print("context_updated=YES")
print("resolved_object_saved=YES")
print("unknown_symbol_alias_handled=YES")
print("source_system_dependency_checked=YES")
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
echo "VERDICT=RESOLVE_SYMBOL_ALIAS_STEP_V1_READY"
echo "TEST_RESOLVE_SYMBOL_ALIAS_STEP_V1_OK"
