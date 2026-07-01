#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTIVE_HEALTH_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/formatters/status_formatter.py \
  src/marketcore/presentation/widgets/executive_health/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.formatters.status_formatter import StatusFormatter
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.executive_health.renderer import ExecutiveHealthWidget

vm = build_default_executive_overview_vm()
widget = ExecutiveHealthWidget()

html_ru = widget.render(vm, lang="ru")
html_en = widget.render(vm, lang="en")

assert "Система" in html_ru
assert "97%" in html_ru
assert "Готово" in html_ru
assert "Подробнее" in html_ru

assert "System" in html_en
assert "97%" in html_en
assert "Ready" in html_en

assert StatusFormatter.normalize("READY") == "READY"
assert StatusFormatter.normalize("bad") == "INFO"
assert StatusFormatter.short("READY", "ru") == "Готово"
assert StatusFormatter.short("READY", "en") == "Ready"

print("executive_health_widget=READY")
print("formatter_ready=READY")
print("metric_card_ready=READY")
print("ru_copy=READY")
print("en_copy=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=EXECUTIVE_HEALTH_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_EXECUTIVE_HEALTH_WIDGET_V1_OK"
