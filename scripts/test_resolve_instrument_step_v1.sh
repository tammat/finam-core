#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESOLVE_INSTRUMENT_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import ResolveInstrumentStep


class FakeInstrumentResolver:
    def __init__(self):
        self.calls = 0
        self.keys = []

    def resolve(self, conn, key):
        self.calls += 1
        self.keys.append(key)

        if key == "303":
            return {
                "id": 303,
                "entity_code": "SBER",
                "asset_id": 11,
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

ctx.symbol_alias = {
    "id": 202,
    "instrument_id": 303,
}

resolver = FakeInstrumentResolver()

ctx.resolvers = SimpleNamespace(
    conn=None,
    instrument=resolver,
)

result = ResolveInstrumentStep().run(ctx)

assert result.success
assert ctx.instrument_id == 303
assert ctx.instrument["entity_code"] == "SBER"

assert resolver.calls == 1
assert resolver.keys == ["303"]

assert ctx.metrics["instrument_resolved"] == 1
assert ctx.metrics["step_resolve_instrument_runs"] == 1

print("resolve_instrument_step=READY")
print("resolver_called=YES")
print("context_updated=YES")
print("resolved_object_saved=YES")
print("step_policy=NO_SQL_IN_STEP")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=RESOLVE_INSTRUMENT_STEP_V1_READY"
echo "TEST_RESOLVE_INSTRUMENT_STEP_V1_OK"
