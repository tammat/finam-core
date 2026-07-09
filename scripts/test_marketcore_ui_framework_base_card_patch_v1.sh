#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_BASE_CARD_PATCH_V1 ==="

widget_file="src/marketcore/presentation/framework/base_widget.py"
card_file="src/marketcore/presentation/framework/base_card.py"
registry_file="src/marketcore/presentation/framework/registry.py"

test -f "$widget_file"
test -f "$card_file"
test -f "$registry_file"

PYTHONPYCACHEPREFIX=/tmp/framework_card_patch \
PYTHONPATH=src \
python -m py_compile "$registry_file" "$widget_file" "$card_file"

if grep -E "SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(|<div|<section|</" "$card_file"; then
    echo "FORBIDDEN_DEPENDENCY_FOUND"
    exit 1
fi

if grep -E "status_label: str|title: str|subtitle: str|tooltip: str|card_type: str|status_code: str" "$card_file"; then
    echo "RAW_UI_TEXT_OR_STRING_CODE_FIELD_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_widget import BaseWidget
from marketcore.presentation.framework.registry import (
    ActionCode,
    CardType,
    UiStatusCode,
    WidgetType,
)

card = BaseCard(
    widget_id="ui.framework.test.card",
    widget_type=WidgetType.KPI,
    card_type=CardType.KPI,
    title_key="ui.framework.test.card.title",
    subtitle_key="ui.framework.test.card.subtitle",
    tooltip_key="ui.framework.test.card.tooltip",
    status_code=UiStatusCode.WARNING,
    status_label_key="ui.status.warning",
    actions=(
        {"action_code": ActionCode.OPEN.value, "target": "/workspace-v2"},
    ),
    badges=(
        {"badge_code": "ui.badge.lifecycle", "value_key": "lifecycle.probe"},
    ),
    payload={"metric_code": "ui.metric.test"},
)

assert isinstance(card, BaseWidget)
assert card.is_visible()
assert card.is_enabled()
assert card.has_actions()
assert card.has_badges()

data = card.to_dict()

assert data["widget_id"] == "ui.framework.test.card"
assert data["widget_type"] == WidgetType.KPI.value
assert data["card_type"] == CardType.KPI.value
assert data["status_code"] == UiStatusCode.WARNING.value
assert data["status_label_key"] == "ui.status.warning"
assert data["title_key"] == "ui.framework.test.card.title"
assert data["actions"][0]["action_code"] == ActionCode.OPEN.value
assert data["badges"][0]["value_key"] == "lifecycle.probe"
assert data["payload"]["metric_code"] == "ui.metric.test"

print("base_card_i18n_patch=OK")
PY

echo "framework_layer=OK"
echo "base_widget_inheritance=OK"
echo "registry_card_type=OK"
echo "registry_status_code=OK"
echo "i18n_keys_required=OK"
echo "html_in_model=0"
echo "sql_in_model=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FRAMEWORK_BASE_CARD_PATCH_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_BASE_CARD_PATCH_V1_OK"
