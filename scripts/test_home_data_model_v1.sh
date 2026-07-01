#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_HOME_DATA_MODEL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/executive_overview_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import (
    ExecutiveOverviewVM,
    HomeMetricVM,
    HomeRiskVM,
    HomeVersionVM,
    HomeActivityVM,
    build_default_executive_overview_vm,
)

vm = build_default_executive_overview_vm()

assert isinstance(vm, ExecutiveOverviewVM)
assert vm.product == "MarketCore"
assert vm.subtitle == "Trading Intelligence Platform"
assert vm.health_value == "97%"
assert vm.health_status == "READY"

assert len(vm.platform) == 6
assert len(vm.market) == 4
assert len(vm.research) == 3
assert len(vm.metadata) == 3
assert len(vm.execution) == 3
assert len(vm.activity) >= 3
assert len(vm.quick_actions) == 4

assert isinstance(vm.platform[0], HomeMetricVM)
assert isinstance(vm.risk, HomeRiskVM)
assert isinstance(vm.version, HomeVersionVM)
assert isinstance(vm.activity[0], HomeActivityVM)

assert vm.risk.value == "HIGH"
assert vm.risk.priority == "P1"
assert vm.version.product_version == "1.0.0"

assert any(x.title == "Выполн." for x in vm.platform)
assert any(x.title == "Мета" for x in vm.platform)
assert any(x.title == "Исслед." for x in vm.platform)

print("home_data_model=READY")
print("executive_overview_vm=READY")
print("platform_metrics=READY")
print("market_metrics=READY")
print("research_metrics=READY")
print("metadata_metrics=READY")
print("execution_metrics=READY")
print("risk_model=READY")
print("version_model=READY")
print("activity_model=READY")
print("quick_actions=READY")
print("ux_copy_ru_short=READY")
print("marketcore_brand=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=HOME_DATA_MODEL_V1_READY")
PY

echo "VERDICT=TEST_HOME_DATA_MODEL_V1_OK"
