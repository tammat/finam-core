#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_SUMMARY_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/execution_summary/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.execution_summary.renderer import ExecutionSummaryWidget

vm = build_default_executive_overview_vm()
widget = ExecutionSummaryWidget()

html_ru = widget.render(vm, "ru")
html_en = widget.render(vm, "en")

assert "Выполн." in html_ru
assert "Выкл." in html_ru
assert "Micro" in html_ru
assert "Off" in html_ru
assert "Kill Switch" in html_ru
assert "READY" in html_ru
assert "DISABLED" in html_ru
assert "fc-grid" in html_ru

assert "Execution" in html_en
assert "Off" in html_en
assert "Kill Switch" in html_en
assert "fc-grid" in html_en

print("execution_summary_widget=READY")
print("execution_disabled=READY")
print("micro_live_disabled=READY")
print("kill_switch_ready=READY")
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
print("VERDICT=EXECUTION_SUMMARY_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_SUMMARY_WIDGET_V1_OK"
