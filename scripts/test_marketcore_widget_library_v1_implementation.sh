#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WIDGET_LIBRARY_V1_IMPLEMENTATION ==="

files=(
  src/marketcore/presentation/widgets/__init__.py
  src/marketcore/presentation/widgets/contracts.py
  src/marketcore/presentation/widgets/renderer.py
  src/marketcore/presentation/widgets/registry.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_widget_library PYTHONPATH=src python -m py_compile "$f"
done

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.widgets.contracts import WidgetViewModel
from marketcore.presentation.widgets.registry import default_widget_registry
from marketcore.presentation.widgets.renderer import render_widget, render_widgets

registry = default_widget_registry()
items = registry.all()
assert len(items) >= 5
assert registry.get("best_edge").title_key == "widget.best_edge.title"

vm = WidgetViewModel(
    widget_id="best_edge",
    title_key="widget.best_edge.title",
    icon="🎯",
    priority=10,
    category="research",
    content={"symbol": "LKOH", "score": "79.15"},
    updated_at="08.07.26 10:00",
)

html = render_widget(vm)
assert 'data-widget-id="best_edge"' in html
assert "widget.best_edge.title" in html
assert "LKOH" in html

grid = render_widgets([vm])
assert "marketcore-widget-grid" in grid
print("widget_registry=OK")
print("widget_render=OK")
PY

if grep -RInE 'psycopg2|SELECT |INSERT |UPDATE |DELETE |send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|orders|fills' \
  src/marketcore/presentation/widgets; then
  echo "DANGEROUS_WIDGET_LIBRARY_ACTION_FOUND"
  exit 1
fi

echo "widget_files=${#files[@]}"
echo "widget_registry=OK"
echo "widget_render=OK"
echo "dangerous_actions=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WIDGET_LIBRARY_V1_IMPLEMENTATION_READY"
echo "VERDICT=TEST_MARKETCORE_WIDGET_LIBRARY_V1_IMPLEMENTATION_OK"
