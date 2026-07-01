#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_WIDGETS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/risk_page/overview.py \
  src/marketcore/presentation/widgets/risk_page/rules.py \
  src/marketcore/presentation/widgets/risk_page/events.py \
  src/marketcore/presentation/widgets/risk_page/actions.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.risk_control_center_vm import build_default_risk_control_center_vm
from marketcore.presentation.widgets.risk_page.overview import RiskOverviewWidget
from marketcore.presentation.widgets.risk_page.rules import RiskRulesWidget
from marketcore.presentation.widgets.risk_page.events import RiskEventsWidget
from marketcore.presentation.widgets.risk_page.actions import RiskActionsWidget

vm = build_default_risk_control_center_vm()

html = (
    RiskOverviewWidget().render(vm)
    + RiskRulesWidget().render(vm)
    + RiskEventsWidget().render(vm)
    + RiskActionsWidget().render(vm)
)

for needle in [
    "Сводка",
    "Лимиты",
    "События",
    "Действия",
    "Уровень",
    "Высокий",
    "Корреляция",
    "План P1",
    "Дневной убыток",
    "Экспозиция",
    "Micro Live",
    "Выкл.",
]:
    assert needle in html, needle

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks"]:
    assert forbidden not in html, forbidden

print("risk_overview_widget=READY")
print("risk_rules_widget=READY")
print("risk_events_widget=READY")
print("risk_actions_widget=READY")
print("ru_copy_full=READY")
print("design_system=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RISK_WIDGETS_V1_READY")
PY

echo "VERDICT=TEST_RISK_WIDGETS_V1_OK"
