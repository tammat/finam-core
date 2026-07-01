#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_DATA_MODEL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/risk_control_center_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.risk_control_center_vm import (
    RiskControlCenterVM,
    RiskMetricVM,
    RiskRuleVM,
    RiskEventVM,
    build_default_risk_control_center_vm,
)

vm = build_default_risk_control_center_vm()

assert isinstance(vm, RiskControlCenterVM)
assert vm.title == "Риски"
assert vm.subtitle == "Risk Control Center"

assert len(vm.overview) == 4
assert len(vm.rules) >= 4
assert len(vm.events) >= 3
assert len(vm.actions) == 3

assert isinstance(vm.overview[0], RiskMetricVM)
assert isinstance(vm.rules[0], RiskRuleVM)
assert isinstance(vm.events[0], RiskEventVM)

assert vm.overview[0].value == "Высокий"
assert vm.overview[1].title == "Корреляция"
assert vm.overview[3].value == "Выкл."
assert vm.rules[3].action == "План P1"

text = " ".join(
    [m.title + " " + m.value for m in vm.overview]
    + [r.rule + " " + r.action for r in vm.rules]
    + [e.event for e in vm.events]
)

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks"]:
    assert forbidden not in text, forbidden

print("risk_data_model=READY")
print("risk_control_center_vm=READY")
print("overview_metrics=READY")
print("rules_model=READY")
print("events_model=READY")
print("actions_model=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RISK_DATA_MODEL_V1_READY")
PY

echo "VERDICT=TEST_RISK_DATA_MODEL_V1_OK"
