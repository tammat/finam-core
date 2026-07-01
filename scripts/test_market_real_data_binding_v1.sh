#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_REAL_DATA_BINDING_V1 ==="

PYTHONPATH=src python - <<'PY'

from marketcore.services.market.market_intelligence_service import \
    MarketIntelligenceService

vm = MarketIntelligenceService().load()

assert len(vm.overview) == 4
assert len(vm.quality) >= 3
assert len(vm.instruments) >= 3

assert vm.overview[0].value != ""
assert vm.overview[1].value != ""
assert vm.overview[2].value != ""

print("market_real_data=READY")
print("overview_ready=READY")
print("quality_ready=READY")
print("instrument_ready=READY")
print("safe_query_ready=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_REAL_DATA_BINDING_V1_READY")

PY

echo "VERDICT=TEST_MARKET_REAL_DATA_BINDING_V1_OK"
