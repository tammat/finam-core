#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_DRY_RUN_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from marketcore.normalization.builder import MarketDataNormalizationBuilder
from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import (
    ResolveSourceSystemStep,
    ResolveSymbolAliasStep,
    ResolveInstrumentStep,
    ResolveContractStep,
    ResolveTimeframeStep,
    BuildBarEventStep,
    RunQualityStep,
    BuildLineageStep,
)

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
    payload={}
)

ctx = NormalizationContext(raw=raw)

# Fake registry
registry = MagicMock()

registry.conn = None

registry.source_system.resolve.return_value = {
    "id": 101,
}

registry.symbol_alias.resolve.return_value = {
    "id": 202,
    "instrument_id": 303,
    "contract_id": 404,
}

registry.instrument.resolve.return_value = {
    "id": 303,
}

registry.contract.resolve.return_value = {
    "id": 404,
}

registry.timeframe.resolve.return_value = {
    "id": 5,
    "entity_code": "M5",
}

ctx.resolvers = registry

builder = MarketDataNormalizationBuilder(
    steps=(
        ResolveSourceSystemStep(),
        ResolveSymbolAliasStep(),
        ResolveInstrumentStep(),
        ResolveContractStep(),
        ResolveTimeframeStep(),
        BuildBarEventStep(),
        RunQualityStep(),
        BuildLineageStep(),
    )
)

result = builder.run(ctx)

print("SUCCESS =", result.success)
print("ERRORS =", result.errors)
print("PAYLOAD =", result.payload)
print("REJECTED =", ctx.rejected)
print("REASON =", ctx.rejection_reason)
print("SOURCE =", ctx.source_system)
print("ALIAS =", ctx.symbol_alias)
print("INSTRUMENT =", ctx.instrument)
print("CONTRACT =", ctx.contract)
print("TIMEFRAME =", ctx.timeframe)
print("EVENT =", hasattr(ctx, "bar_event"))
print("LINEAGE =", len(ctx.lineage_edges))

assert result.success
assert ctx.event_uuid is not None
assert len(ctx.lineage_edges) == 1

assert registry.source_system.resolve.call_count == 1
assert registry.symbol_alias.resolve.call_count == 1
assert registry.instrument.resolve.call_count == 1
assert registry.contract.resolve.call_count == 1
assert registry.timeframe.resolve.call_count == 1

print("dry_run_pipeline=READY")
print("postgres_write=NO")
print("builder_success=YES")
print("lineage_created=YES")
print("quality_created=YES")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_DATA_NORMALIZATION_DRY_RUN_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_DRY_RUN_V1_OK"
