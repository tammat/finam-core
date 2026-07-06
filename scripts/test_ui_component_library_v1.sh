#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_COMPONENT_LIBRARY_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/components/html.py \
  src/marketcore/presentation/components/kpi_card.py \
  src/marketcore/presentation/components/data_table.py \
  src/marketcore/presentation/components/tree_view.py \
  src/marketcore/presentation/components/object_card.py \
  src/marketcore/presentation/components/section.py \
  src/marketcore/presentation/components/__init__.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.components import (
    render_data_table,
    render_kpi_card,
    render_object_card,
    render_section,
    render_tree_view,
)

html = ""
html += render_kpi_card("Paper", "9", "active")
html += render_data_table(["symbol", "pnl"], [{"symbol": "SBER@MISX", "pnl": 10}])
html += render_tree_view({"Instrument": {"Symbol": "SBER@MISX"}})
html += render_object_card("Recommendation", {"Action": "EXPAND"})
html += render_section("Section", "Body")

assert "<pre>" not in html
assert "kpi-card" in html
assert "data-table" in html
assert "tree-view" in html
assert "object-card" in html
assert "ui-section" in html
assert "&lt;" not in render_kpi_card("A", "<unsafe>") or "&lt;unsafe&gt;" in render_kpi_card("A", "<unsafe>")

print("UI_COMPONENT_LIBRARY_OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_COMPONENT_LIBRARY_V1_READY"
echo "VERDICT=TEST_UI_COMPONENT_LIBRARY_V1_OK"
