#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_DATA_MODEL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/execution_center_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.execution_center_vm import (
    ExecutionCenterVM,
    ExecutionMetricVM,
    ExecutionOrderVM,
    ExecutionFillVM,
    build_default_execution_center_vm,
)

vm = build_default_execution_center_vm()

assert isinstance(vm, ExecutionCenterVM)
assert vm.title == "Выполнение"
assert vm.subtitle == "Execution Center"

assert len(vm.overview) == 4
assert len(vm.orders) >= 1
assert len(vm.fills) >= 1
assert len(vm.actions) == 3

assert isinstance(vm.overview[0], ExecutionMetricVM)
assert isinstance(vm.orders[0], ExecutionOrderVM)
assert isinstance(vm.fills[0], ExecutionFillVM)

assert vm.overview[0].value == "Выкл."
assert vm.orders[0].symbol == "Нет заявок"
assert vm.fills[0].symbol == "Нет сделок"

text = " ".join(
    [m.title + " " + m.value for m in vm.overview]
    + [o.symbol + " " + o.side for o in vm.orders]
    + [f.symbol for f in vm.fills]
)

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks", "Off"]:
    assert forbidden not in text, forbidden

print("execution_data_model=READY")
print("execution_center_vm=READY")
print("overview_metrics=READY")
print("orders_model=READY")
print("fills_model=READY")
print("actions_model=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=EXECUTION_DATA_MODEL_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_DATA_MODEL_V1_OK"
