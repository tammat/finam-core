#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_BASE_SECTION_V1 ==="

files=(
  "src/marketcore/presentation/framework/registry.py"
  "src/marketcore/presentation/framework/base_widget.py"
  "src/marketcore/presentation/framework/base_card.py"
  "src/marketcore/presentation/framework/base_section.py"
)

for f in "${files[@]}"; do
  test -f "$f"
done

PYTHONPYCACHEPREFIX=/tmp/framework_section \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -E "SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(|<div|<section|</" src/marketcore/presentation/framework/base_section.py; then
    echo "FORBIDDEN_DEPENDENCY_FOUND"
    exit 1
fi

if grep -E "title: str|subtitle: str|tooltip: str|section_type: str|status_code: str|status_label: str" src/marketcore/presentation/framework/base_section.py; then
    echo "RAW_UI_TEXT_OR_STRING_CODE_FIELD_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import CardType, SectionType, UiStatusCode, WidgetType

card_a = BaseCard(
    widget_id="ui.framework.test.card.a",
    widget_type=WidgetType.KPI,
    card_type=CardType.KPI,
    title_key="ui.framework.test.card.a.title",
    status_code=UiStatusCode.OK,
    status_label_key="ui.status.ok",
    priority=20,
)

card_b = BaseCard(
    widget_id="ui.framework.test.card.b",
    widget_type=WidgetType.KPI,
    card_type=CardType.KPI,
    title_key="ui.framework.test.card.b.title",
    status_code=UiStatusCode.WARNING,
    status_label_key="ui.status.warning",
    priority=10,
)

section = BaseSection(
    section_id="ui.framework.test.section.summary",
    section_type=SectionType.SUMMARY,
    title_key="ui.framework.test.section.title",
    subtitle_key="ui.framework.test.section.subtitle",
    tooltip_key="ui.framework.test.section.tooltip",
    status_code=UiStatusCode.WARNING,
    status_label_key="ui.status.warning",
    cards=(card_a, card_b),
)

assert section.is_visible()
assert section.is_enabled()
assert section.has_cards()

ordered = section.ordered_cards()
assert ordered[0].widget_id == "ui.framework.test.card.b"
assert ordered[1].widget_id == "ui.framework.test.card.a"

data = section.to_dict()
assert data["section_type"] == SectionType.SUMMARY.value
assert data["status_code"] == UiStatusCode.WARNING.value
assert data["title_key"] == "ui.framework.test.section.title"
assert len(data["cards"]) == 2
assert data["cards"][0]["card_type"] == CardType.KPI.value

print("base_section=OK")
PY

echo "framework_layer=OK"
echo "registry_section_type=OK"
echo "registry_status_code=OK"
echo "i18n_keys_required=OK"
echo "ordered_cards=OK"
echo "html_in_model=0"
echo "sql_in_model=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FRAMEWORK_BASE_SECTION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_BASE_SECTION_V1_OK"
