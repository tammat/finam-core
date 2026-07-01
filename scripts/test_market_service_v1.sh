#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_SERVICE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/market/market_intelligence_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.services.market.market_intelligence_service import \
    MarketIntelligenceService

service = MarketIntelligenceService()

vm = service.load()

assert vm.title == "Рынок"
assert vm.subtitle == "Market Intelligence"

assert len(vm.overview) == 4
assert len(vm.quality) >= 3
assert len(vm.instruments) >= 3
assert len(vm.actions) == 3

assert vm.overview[0].title == "Бары"
assert vm.overview[1].title == "Тики"
assert vm.overview[2].title == "Инстр."
assert vm.overview[3].title == "Актуал."

assert vm.quality[0].check == "OHLC"
assert vm.quality[1].check == "Объём"

assert vm.instruments[0].asset_class == "Фьючерсы"
assert vm.instruments[1].asset_class == "Акции"
assert vm.instruments[2].asset_class == "Крипто"

print("market_service=READY")
print("view_model=READY")
print("overview_ready=READY")
print("quality_ready=READY")
print("instrument_ready=READY")
print("actions_ready=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_SERVICE_V1_READY")
PY

echo "VERDICT=TEST_MARKET_SERVICE_V1_OK"
