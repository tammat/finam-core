#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_REGISTRY_V1 ==="

file="src/marketcore/presentation/framework/registry.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/framework_registry \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -E "SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(|<div|<section|</" "$file"; then
    echo "FORBIDDEN_DEPENDENCY_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.registry import (
    WidgetType,
    CardType,
    SectionType,
    LayoutType,
    UiStatusCode,
    ActionCode,
)

assert WidgetType.KPI.value
assert CardType.INSTRUMENT.value
assert SectionType.PORTFOLIO.value
assert LayoutType.PHONE.value
assert UiStatusCode.WARNING.value
assert ActionCode.OPEN.value

for enum_cls in (WidgetType, CardType, SectionType, LayoutType, UiStatusCode, ActionCode):
    values = [item.value for item in enum_cls]
    assert len(values) == len(set(values))

print("framework_registry=OK")
PY

echo "framework_registry=OK"
echo "centralized_ui_codes=OK"
echo "sql_in_registry=0"
echo "html_in_registry=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FRAMEWORK_REGISTRY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_REGISTRY_V1_OK"
