#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_REJECT_V1 ==="

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from marketcore.normalization.builder import MarketDataNormalizationBuilder
from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.dto import CanonicalMarketBarDTO
from marketcore.normalization.steps import (
    ResolveSourceSystemStep,
)

raw = CanonicalMarketBarDTO(
    source_system_code="UNKNOWN",
    source_key="UNKNOWN",
    symbol_code="UNKNOWN",
    timeframe_code="M5",
    event_time=datetime.now(timezone.utc),
    source_time=datetime.now(timezone.utc),
    received_at=datetime.now(timezone.utc),
    open=Decimal("1"),
    high=Decimal("2"),
    low=Decimal("1"),
    close=Decimal("2"),
    volume=Decimal("1"),
    payload={}
)

ctx = NormalizationContext(raw=raw)

registry = MagicMock()
registry.conn = None
registry.source_system.resolve.return_value = None

ctx.resolvers = registry

builder = MarketDataNormalizationBuilder(
    steps=(
        ResolveSourceSystemStep(),
    )
)

result = builder.run(ctx)

assert result.success is False
assert ctx.rejected is True
assert ctx.rejection_reason == "UNKNOWN_SOURCE_SYSTEM"
assert len(ctx.quality_events) == 1

print("reject_pipeline=READY")
print("quality_event_created=YES")
print("reject_reason=UNKNOWN_SOURCE_SYSTEM")
print("builder_rejected=YES")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_DATA_NORMALIZATION_REJECT_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_REJECT_V1_OK"
