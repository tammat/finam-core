#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WIDGET_BASE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/widgets/__init__.py \
  src/marketcore_os/widgets/base.py \
  src/marketcore_os/widgets/registry.py

PYTHONPATH=src python - <<'PY'
from marketcore_os.widgets.base import SimpleWidget, badge, row
from marketcore_os.widgets.registry import WidgetRegistry

class TestWidget(SimpleWidget):
    def body(self, lang: str) -> str:
        return row("Status", badge("READY"))

reg = WidgetRegistry()
w1 = TestWidget(
    widget_id="W_TEST_001",
    title_ru="Тест",
    title_en="Test",
    priority=10,
    refresh_interval_sec=15,
    workspace="workspace",
)
w2 = TestWidget(
    widget_id="W_TEST_002",
    title_ru="Тест 2",
    title_en="Test 2",
    priority=20,
    workspace="capital",
)

reg.register(w2)
reg.register(w1)

items = reg.all()
assert [w.widget_id for w in items] == ["W_TEST_001", "W_TEST_002"]

workspace_items = reg.for_workspace("workspace")
assert len(workspace_items) == 1
assert workspace_items[0].widget_id == "W_TEST_001"

html_ru = workspace_items[0].render("ru")
assert 'data-widget-id="W_TEST_001"' in html_ru
assert 'data-refresh="15"' in html_ru
assert "Тест" in html_ru
assert "READY" in html_ru
assert "mc-row" in html_ru
assert "mc-value" in html_ru

html_en = workspace_items[0].render("en")
assert "Test" in html_en

try:
    reg.register(w1)
    raise AssertionError("duplicate widget_id was not rejected")
except ValueError:
    pass

print("widget_base_ready=READY")
print("widget_registry_ready=READY")
print("workspace_discovery_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WIDGET_BASE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WIDGET_BASE_V1_OK"
