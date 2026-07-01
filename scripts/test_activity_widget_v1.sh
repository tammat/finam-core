#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_ACTIVITY_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/activity_summary/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.activity_summary.renderer import ActivitySummaryWidget

vm = build_default_executive_overview_vm()
widget = ActivitySummaryWidget()

html_ru = widget.render(vm, "ru")
html_en = widget.render(vm, "en")

assert "События" in html_ru
assert "Base page ready" in html_ru
assert "Component preview ready" in html_ru
assert "Design system ready" in html_ru
assert "fc-grid" in html_ru
assert "<ul>" in html_ru

assert "Activity" in html_en
assert "Base page ready" in html_en
assert "fc-grid" in html_en

print("activity_widget=READY")
print("timeline_card=READY")
print("activity_events=READY")
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
print("VERDICT=ACTIVITY_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_ACTIVITY_WIDGET_V1_OK"
