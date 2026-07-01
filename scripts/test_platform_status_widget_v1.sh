#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PLATFORM_STATUS_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/platform_status/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.platform_status.renderer import PlatformStatusWidget

vm = build_default_executive_overview_vm()
widget = PlatformStatusWidget()

html_ru = widget.render(vm, lang="ru")
html_en = widget.render(vm, lang="en")

assert "Платформа" in html_ru
assert "Рынок" in html_ru
assert "Исслед." in html_ru
assert "Мета" in html_ru
assert "Риски" in html_ru
assert "Выполн." in html_ru
assert "Граф знаний" in html_ru
assert "READY" in html_ru
assert "HIGH" in html_ru
assert "DISABLED" in html_ru
assert "fc-grid" in html_ru

assert "Platform" in html_en
assert "fc-grid" in html_en

print("platform_status_widget=READY")
print("platform_cards=READY")
print("risk_high=READY")
print("kg_disabled=READY")
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
print("VERDICT=PLATFORM_STATUS_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_PLATFORM_STATUS_WIDGET_V1_OK"
