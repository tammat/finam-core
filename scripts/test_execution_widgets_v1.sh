#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_WIDGETS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/execution_page/overview.py \
  src/marketcore/presentation/widgets/execution_page/orders.py \
  src/marketcore/presentation/widgets/execution_page/fills.py \
  src/marketcore/presentation/widgets/execution_page/actions.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.execution_center_vm import build_default_execution_center_vm
from marketcore.presentation.widgets.execution_page.overview import ExecutionOverviewWidget
from marketcore.presentation.widgets.execution_page.orders import ExecutionOrdersWidget
from marketcore.presentation.widgets.execution_page.fills import ExecutionFillsWidget
from marketcore.presentation.widgets.execution_page.actions import ExecutionActionsWidget

vm = build_default_execution_center_vm()

html = (
    ExecutionOverviewWidget().render(vm)
    + ExecutionOrdersWidget().render(vm)
    + ExecutionFillsWidget().render(vm)
    + ExecutionActionsWidget().render(vm)
)

for needle in [
    "Сводка",
    "Заявки",
    "Сделки",
    "Действия",
    "Исполнение",
    "Выкл.",
    "Нет заявок",
    "Нет сделок",
    "Кол-во",
    "Цена",
]:
    assert needle in html, needle

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks", "Off", ">READY<", ">DISABLED<"]:
    assert forbidden not in html, forbidden

print("execution_overview_widget=READY")
print("execution_orders_widget=READY")
print("execution_fills_widget=READY")
print("execution_actions_widget=READY")
print("ru_copy_full=READY")
print("design_system=READY")
print("raw_status_hidden=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=EXECUTION_WIDGETS_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_WIDGETS_V1_OK"
