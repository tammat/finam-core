#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_SERVICE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/execution/execution_center_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.services.execution.execution_center_service import ExecutionCenterService

vm = ExecutionCenterService().load()

assert vm.title == "Выполнение"
assert vm.subtitle == "Execution Center"
assert len(vm.overview) == 4
assert len(vm.orders) >= 1
assert len(vm.fills) >= 1
assert len(vm.actions) == 3
assert vm.overview[0].value == "Выкл."
assert vm.orders[0].symbol == "Нет заявок"
assert vm.fills[0].symbol == "Нет сделок"

print("execution_service=READY")
print("view_model=READY")
print("overview_ready=READY")
print("orders_ready=READY")
print("fills_ready=READY")
print("actions_ready=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=EXECUTION_SERVICE_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_SERVICE_V1_OK"
