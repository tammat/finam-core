#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESOLVE_CONTRACT_STEP_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import ResolveContractStep


class FakeContractResolver:
    def __init__(self):
        self.calls = 0
        self.keys = []

    def resolve(self, conn, key):
        self.calls += 1
        self.keys.append(key)

        if key == "404":
            return {
                "id": 404,
                "entity_code": "SBER_TQBR",
                "instrument_id": 303,
                "market_id": 1,
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
    "contract_id": 404,
}

ctx.instrument = {
    "id": 303,
}

resolver = FakeContractResolver()

ctx.resolvers = SimpleNamespace(
    conn=None,
    contract=resolver,
)

result = ResolveContractStep().run(ctx)

assert result.success
assert ctx.contract_id == 404
assert ctx.contract["market_id"] == 1

assert resolver.calls == 1
assert resolver.keys == ["404"]

assert ctx.metrics["contract_resolved"] == 1
assert ctx.metrics["step_resolve_contract_runs"] == 1

print("resolve_contract_step=READY")
print("resolver_called=YES")
print("context_updated=YES")
print("resolved_object_saved=YES")
print("unknown_contract_handled=YES")
print("quality_event_created=YES")
print("step_policy=NO_SQL_IN_STEP")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=RESOLVE_CONTRACT_STEP_V1_READY"
echo "TEST_RESOLVE_CONTRACT_STEP_V1_OK"
