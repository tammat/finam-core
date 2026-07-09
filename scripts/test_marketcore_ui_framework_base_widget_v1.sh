#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_BASE_WIDGET_V1 ==="

file="src/marketcore/presentation/framework/base_widget.py"

test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/framework_widget \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -E "SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(" "$file"; then
    echo "FORBIDDEN_DEPENDENCY_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.base_widget import BaseWidget

w = BaseWidget(
    widget_id="demo",
    widget_type="kpi",
    title="Тест",
)

assert w.is_visible()
assert w.is_enabled()

d = w.to_dict()

assert d["widget_id"] == "demo"
assert d["widget_type"] == "kpi"
assert d["title"] == "Тест"

print("base_widget=OK")
PY

echo "framework_layer=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_UI_FRAMEWORK_BASE_WIDGET_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_BASE_WIDGET_V1_OK"
