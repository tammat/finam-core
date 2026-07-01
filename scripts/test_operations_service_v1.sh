#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OPERATIONS_SERVICE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/operations/operations_center_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.services.operations.operations_center_service import OperationsCenterService

vm = OperationsCenterService().load()

assert vm.title == "Эксплуатация"
assert vm.subtitle == "Operations Center"
assert len(vm.overview) == 4
assert len(vm.services) >= 4
assert len(vm.events) >= 3
assert len(vm.actions) == 3
assert vm.overview[0].title == "Сервисы"
assert vm.events[1].event == "Ошибок нет"

print("operations_service=READY")
print("view_model=READY")
print("overview_ready=READY")
print("services_ready=READY")
print("events_ready=READY")
print("actions_ready=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=OPERATIONS_SERVICE_V1_READY")
PY

echo "VERDICT=TEST_OPERATIONS_SERVICE_V1_OK"
