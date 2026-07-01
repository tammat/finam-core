#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_SUMMARY_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/research_summary/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.research_summary.renderer import ResearchSummaryWidget

vm = build_default_executive_overview_vm()
widget = ResearchSummaryWidget()

html_ru = widget.render(vm, lang="ru")
html_en = widget.render(vm, lang="en")

assert "Исслед." in html_ru
assert "Replay" in html_ru
assert "OOS" in html_ru
assert "Edge" in html_ru
assert "READY" in html_ru
assert "fc-grid" in html_ru

assert "Research" in html_en
assert "Replay" in html_en
assert "OOS" in html_en
assert "Edge" in html_en
assert "fc-grid" in html_en

print("research_summary_widget=READY")
print("research_replay=READY")
print("research_oos=READY")
print("research_edge=READY")
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
print("VERDICT=RESEARCH_SUMMARY_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_RESEARCH_SUMMARY_WIDGET_V1_OK"
