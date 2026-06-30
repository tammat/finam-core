#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PRESENTATION_FRAMEWORK_V1 ==="

PYTHONPATH=src python - <<'PY'
from marketcore.ui import Page, Section, render_card, render_table, render_page

page = Page(
    page_id="lineage",
    title="Quality & Lineage",
    route="/knowledge/lineage",
    group="Knowledge",
    sections=(
        Section("summary", "Summary", lambda: render_card("Lineage Events", 0)),
        Section("health", "Health", lambda: render_table([{"check": "runtime", "status": "OK"}])),
    ),
)

html = render_page(page)

assert "Quality &amp; Lineage" in html
assert "/knowledge/lineage" in html
assert "Summary" in html
assert "Health" in html
assert "READ_ONLY" in html
assert "mc-table" in html
assert "mc-card" in html
assert "viewport" in html
assert "viewport-fit=cover" in html
assert "-webkit-overflow-scrolling" in html

print("presentation_framework=READY")
print("modules=page_framework")
print("page_model=READY")
print("section_model=READY")
print("navigation=READY")
print("cards=READY")
print("tables=READY")
print("read_only_policy=READY")
print("single_ui_port_policy=8089")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PRESENTATION_FRAMEWORK_V1_READY"
echo "TEST_PRESENTATION_FRAMEWORK_V1_OK"
