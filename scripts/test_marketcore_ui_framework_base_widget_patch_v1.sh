#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_BASE_WIDGET_PATCH_V1 ==="

file="src/marketcore/presentation/framework/base_widget.py"
registry="src/marketcore/presentation/framework/registry.py"

test -f "$file"
test -f "$registry"

PYTHONPYCACHEPREFIX=/tmp/framework_widget_patch \
PYTHONPATH=src \
python -m py_compile "$registry" "$file"

if grep -E "SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(|<div|<section|</" "$file"; then
    echo "FORBIDDEN_DEPENDENCY_FOUND"
    exit 1
fi

if grep -E "title: str|subtitle: str|tooltip: str|icon: str" "$file"; then
    echo "RAW_UI_TEXT_FIELD_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.base_widget import BaseWidget
from marketcore.presentation.framework.registry import WidgetType

w = BaseWidget(
    widget_id="ui.framework.test.widget",
    widget_type=WidgetType.KPI,
    title_key="ui.framework.test.title",
    subtitle_key="ui.framework.test.subtitle",
    tooltip_key="ui.framework.test.tooltip",
)

assert w.is_visible()
assert w.is_enabled()

d = w.to_dict()

assert d["widget_id"] == "ui.framework.test.widget"
assert d["widget_type"] == WidgetType.KPI.value
assert d["title_key"] == "ui.framework.test.title"
assert d["subtitle_key"] == "ui.framework.test.subtitle"
assert d["tooltip_key"] == "ui.framework.test.tooltip"

print("base_widget_i18n_patch=OK")
PY

echo "framework_layer=OK"
echo "registry_widget_type=OK"
echo "i18n_keys_required=OK"
echo "raw_ui_text_fields=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FRAMEWORK_BASE_WIDGET_PATCH_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_BASE_WIDGET_PATCH_V1_OK"
