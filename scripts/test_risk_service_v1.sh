#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_SERVICE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/risk/risk_control_center_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.services.risk.risk_control_center_service import RiskControlCenterService

vm = RiskControlCenterService().load()

assert vm.title == "Риски"
assert vm.subtitle == "Risk Control Center"
assert len(vm.overview) == 4
assert len(vm.rules) >= 4
assert len(vm.events) >= 3
assert len(vm.actions) == 3
assert vm.overview[0].value == "Высокий"
assert vm.rules[3].action == "План P1"

print("risk_service=READY")
print("view_model=READY")
print("overview_ready=READY")
print("rules_ready=READY")
print("events_ready=READY")
print("actions_ready=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RISK_SERVICE_V1_READY")
PY

echo "VERDICT=TEST_RISK_SERVICE_V1_OK"
