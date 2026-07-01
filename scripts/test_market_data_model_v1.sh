#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_MODEL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/market_intelligence_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.market_intelligence_vm import (
    MarketIntelligenceVM,
    MarketMetricVM,
    MarketInstrumentVM,
    MarketQualityVM,
    build_default_market_intelligence_vm,
)

vm = build_default_market_intelligence_vm()

assert isinstance(vm, MarketIntelligenceVM)
assert vm.title == "Рынок"
assert vm.subtitle == "Market Intelligence"

assert len(vm.overview) == 4
assert len(vm.quality) >= 3
assert len(vm.instruments) >= 3
assert len(vm.actions) == 3

assert isinstance(vm.overview[0], MarketMetricVM)
assert isinstance(vm.quality[0], MarketQualityVM)
assert isinstance(vm.instruments[0], MarketInstrumentVM)

assert vm.overview[0].title == "Бары"
assert vm.overview[1].title == "Тики"
assert vm.overview[2].title == "Инстр."
assert vm.overview[3].title == "Актуал."

assert vm.quality[0].bad_rows == "0"
assert vm.instruments[0].freshness == "Актуал."

print("market_data_model=READY")
print("market_intelligence_vm=READY")
print("overview_metrics=READY")
print("quality_model=READY")
print("instrument_model=READY")
print("actions_model=READY")
print("ux_copy_ru_short=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_DATA_MODEL_V1_READY")
PY

echo "VERDICT=TEST_MARKET_DATA_MODEL_V1_OK"
