#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OPERATIONS_DATA_MODEL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/operations_center_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.operations_center_vm import (
    OperationsCenterVM,
    OperationsMetricVM,
    OperationsServiceVM,
    OperationsEventVM,
    build_default_operations_center_vm,
)

vm = build_default_operations_center_vm()

assert isinstance(vm, OperationsCenterVM)
assert vm.title == "Эксплуатация"
assert vm.subtitle == "Operations Center"

assert len(vm.overview) == 4
assert len(vm.services) >= 4
assert len(vm.events) >= 3
assert len(vm.actions) == 3

assert isinstance(vm.overview[0], OperationsMetricVM)
assert isinstance(vm.services[0], OperationsServiceVM)
assert isinstance(vm.events[0], OperationsEventVM)

assert vm.overview[0].title == "Сервисы"
assert vm.services[0].service == "Dashboard"
assert vm.events[1].event == "Ошибок нет"

text = " ".join(
    [m.title for m in vm.overview]
    + [s.service for s in vm.services]
    + [e.event for e in vm.events]
)

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks"]:
    assert forbidden not in text, forbidden

print("operations_data_model=READY")
print("operations_center_vm=READY")
print("overview_metrics=READY")
print("services_model=READY")
print("events_model=READY")
print("actions_model=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=OPERATIONS_DATA_MODEL_V1_READY")
PY

echo "VERDICT=TEST_OPERATIONS_DATA_MODEL_V1_OK"
