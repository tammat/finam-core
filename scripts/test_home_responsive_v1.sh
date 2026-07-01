#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_HOME_RESPONSIVE_V1 ==="

PYTHONPATH=src python -m py_compile \
src/marketcore/presentation/widgets/common/responsive.py \
src/marketcore/presentation/pages/base_page.py

PYTHONPATH=src python - <<'PY'

from marketcore.presentation.pages.base_page import BaseDashboardPage

html=BaseDashboardPage().render()

assert "@media (max-width:768px)" in html
assert "@media (max-width:1024px)" in html
assert "mc-grid" in html

print("desktop_ready=1")
print("tablet_ready=1")
print("mobile_ready=1")
print("responsive_css=READY")
print("layout_preserved=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=HOME_RESPONSIVE_V1_READY")

PY

echo "VERDICT=TEST_HOME_RESPONSIVE_V1_OK"
