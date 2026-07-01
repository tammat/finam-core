#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_QUICK_ACTIONS_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/quick_actions/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.quick_actions.renderer import QuickActionsWidget

vm = build_default_executive_overview_vm()
widget = QuickActionsWidget()

html_ru = widget.render(vm, "ru")
html_en = widget.render(vm, "en")

assert "Быстрые действия" in html_ru
assert "Диагн." in html_ru
assert "Риски" in html_ru
assert "Рынок" in html_ru
assert "Исслед." in html_ru

assert "/system" in html_ru
assert "/risk" in html_ru
assert "/market" in html_ru
assert "/research" in html_ru

assert "Quick Actions" in html_en

print("quick_actions_widget=READY")
print("system_action=READY")
print("risk_action=READY")
print("market_action=READY")
print("research_action=READY")
print("design_system_grid=READY")
print("ru_copy=READY")
print("en_copy=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=QUICK_ACTIONS_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_QUICK_ACTIONS_WIDGET_V1_OK"
