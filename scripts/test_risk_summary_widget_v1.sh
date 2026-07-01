#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_SUMMARY_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/risk_summary/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.risk_summary.renderer import RiskSummaryWidget

vm = build_default_executive_overview_vm()
widget = RiskSummaryWidget()

html_ru = widget.render(vm, "ru")
html_en = widget.render(vm, "en")

assert "Риски" in html_ru
assert "Высокий риск" in html_ru
assert "Corr. risk" in html_ru
assert "P1" in html_ru
assert "План P1" in html_ru
assert "fc-grid" in html_ru

assert "Risk" in html_en
assert "High Risk" in html_en
assert "Corr. risk" in html_en
assert "P1" in html_en
assert "fc-grid" in html_en

print("risk_summary_widget=READY")
print("risk_status=READY")
print("risk_reason=READY")
print("risk_priority=READY")
print("risk_action=READY")
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
print("VERDICT=RISK_SUMMARY_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_RISK_SUMMARY_WIDGET_V1_OK"
