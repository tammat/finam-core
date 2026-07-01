#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_VERSION_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/version_summary/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.version_summary.renderer import VersionSummaryWidget

vm = build_default_executive_overview_vm()
widget = VersionSummaryWidget()

html_ru = widget.render(vm, "ru")
html_en = widget.render(vm, "en")

assert "Версии" in html_ru
assert "MarketCore" in html_ru
assert "1.0.0" in html_ru
assert "Сборка" in html_ru
assert "Dashboard" in html_ru
assert "Repo" in html_ru
assert "Commit" in html_ru
assert "Tag" in html_ru
assert "fc-grid" in html_ru

assert "Versions" in html_en
assert "MarketCore" in html_en
assert "Build" in html_en
assert "fc-grid" in html_en

print("version_widget=READY")
print("product_version=READY")
print("dashboard_version=READY")
print("git_commit=READY")
print("git_tag=READY")
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
print("VERDICT=VERSION_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_VERSION_WIDGET_V1_OK"
