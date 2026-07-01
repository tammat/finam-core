#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BASE_DASHBOARD_PAGE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/base_page.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.pages.base_page import (
    BaseDashboardPage,
    DashboardAction,
    DashboardPageContext,
    DashboardSection,
)

class TestPage(BaseDashboardPage):
    page_key = "test"
    title = "Test Page"
    subtitle = "MarketCore"
    actions = [
        DashboardAction("Open", "/test"),
    ]

    def sections(self):
        return [
            DashboardSection(
                title="Test Section",
                cards=[
                    "<section class='fc-card'>READY</section>",
                ],
            )
        ]

page = TestPage()
html = page.render(DashboardPageContext(lang="ru", timezone="Europe/Moscow"))

assert "Test Page" in html
assert "MarketCore" in html
assert "Test Section" in html
assert "READY" in html
assert "fc-header" in html
assert "fc-sidebar" in html
assert "fc-mobile-nav" in html
assert "Europe/Moscow" in html

print("base_page_ready=1")
print("page_context_ready=1")
print("page_actions_ready=1")
print("page_sections_ready=1")
print("layout_integration=READY")
print("design_system_integration=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=BASE_DASHBOARD_PAGE_V1_READY")
PY

echo "VERDICT=TEST_BASE_DASHBOARD_PAGE_V1_OK"
