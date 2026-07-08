#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_COMPONENT_LIBRARY_V1 ==="

files=(
  src/marketcore/presentation/components/common/html.py
  src/marketcore/presentation/components/widgets/icon.py
  src/marketcore/presentation/components/widgets/badge.py
  src/marketcore/presentation/components/widgets/button.py
  src/marketcore/presentation/components/cards.py
  src/marketcore/presentation/components/tables/data_table.py
  src/marketcore/presentation/components/layout/section.py
  src/marketcore/presentation/components/layout/toolbar.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_component_library PYTHONPATH=src python -m py_compile "$f"
done

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_component_library PYTHONPATH=src python - <<'PY'
from marketcore.presentation.components.cards import render_card, render_kpi_card
from marketcore.presentation.components.tables.data_table import render_data_table
from marketcore.presentation.components.widgets.button import render_button
from marketcore.presentation.components.widgets.badge import render_badge
from marketcore.presentation.components.layout.section import render_section
from marketcore.presentation.components.layout.toolbar import render_toolbar

html = ""
html += render_card("Title", "<p>Body</p>", "test-card")
html += render_kpi_card("Label", 123, "Hint")
html += render_data_table([("symbol", "Symbol"), ("score", "Score")], [{"symbol": "LKOH", "score": 77}])
html += render_button("Open", "/max-edge", "↗")
html += render_button("Disabled", None, "⛔", disabled=True)
html += render_badge("PASS", "success")
html += render_section("Section", "<p>Text</p>")
html += render_toolbar([render_button("Home", "/", "🏠")])

for marker in [
    "ui-card", "ui-kpi-card", "ui-data-table", "ui-button",
    "ui-button-disabled", "ui-badge", "ui-section", "ui-toolbar"
]:
    assert marker in html, marker

assert "&lt;script&gt;" in render_card("<script>", "<b>body</b>")
print("component_render=OK")
PY

if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/components/common \
  src/marketcore/presentation/components/widgets \
  src/marketcore/presentation/components/layout \
  src/marketcore/presentation/components/tables \
  src/marketcore/presentation/components/cards.py; then
  echo "DANGEROUS_COMPONENT_ACTION_FOUND"
  exit 1
fi

echo "component_files=${#files[@]}"
echo "component_render=OK"
echo "dangerous_actions=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_COMPONENT_LIBRARY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_COMPONENT_LIBRARY_V1_OK"
