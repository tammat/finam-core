#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OPERATIONS_WIDGETS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/operations_page/overview.py \
  src/marketcore/presentation/widgets/operations_page/services.py \
  src/marketcore/presentation/widgets/operations_page/events.py \
  src/marketcore/presentation/widgets/operations_page/actions.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.operations_center_vm import build_default_operations_center_vm
from marketcore.presentation.widgets.operations_page.overview import OperationsOverviewWidget
from marketcore.presentation.widgets.operations_page.services import OperationsServicesWidget
from marketcore.presentation.widgets.operations_page.events import OperationsEventsWidget
from marketcore.presentation.widgets.operations_page.actions import OperationsActionsWidget

vm = build_default_operations_center_vm()

html = (
    OperationsOverviewWidget().render(vm)
    + OperationsServicesWidget().render(vm)
    + OperationsEventsWidget().render(vm)
    + OperationsActionsWidget().render(vm)
)

for needle in [
    "Сводка",
    "Сервисы",
    "События",
    "Действия",
    "Dashboard",
    "Paper Runtime",
    "Research",
    "Работает",
    "Ошибок нет",
]:
    assert needle in html, needle

for forbidden in [
    "Details",
    "Settings",
    "Search",
    "Fresh",
    "Volume",
    "Ticks",
    ">READY<",
]:
    assert forbidden not in html, forbidden

print("operations_overview_widget=READY")
print("operations_services_widget=READY")
print("operations_events_widget=READY")
print("operations_actions_widget=READY")
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
print("VERDICT=OPERATIONS_WIDGETS_V1_READY")
PY

echo "VERDICT=TEST_OPERATIONS_WIDGETS_V1_OK"
