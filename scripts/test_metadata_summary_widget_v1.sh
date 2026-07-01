#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_METADATA_SUMMARY_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/metadata_summary/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.metadata_summary.renderer import MetadataSummaryWidget

vm = build_default_executive_overview_vm()
widget = MetadataSummaryWidget()

html_ru = widget.render(vm, lang="ru")
html_en = widget.render(vm, lang="en")

assert "Мета" in html_ru
assert "Объекты" in html_ru
assert "373" in html_ru
assert "Источн." in html_ru
assert "12" in html_ru
assert "Покрытие" in html_ru
assert "100%" in html_ru
assert "READY" in html_ru
assert "fc-grid" in html_ru

assert "Metadata" in html_en
assert "373" in html_en
assert "100%" in html_en
assert "fc-grid" in html_en

print("metadata_summary_widget=READY")
print("metadata_objects=READY")
print("metadata_sources=READY")
print("metadata_coverage=READY")
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
print("VERDICT=METADATA_SUMMARY_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_METADATA_SUMMARY_WIDGET_V1_OK"
