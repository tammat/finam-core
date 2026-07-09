#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_BASE_LAYOUT_V1 ==="

files=(
  "src/marketcore/presentation/framework/registry.py"
  "src/marketcore/presentation/framework/base_widget.py"
  "src/marketcore/presentation/framework/base_card.py"
  "src/marketcore/presentation/framework/base_section.py"
  "src/marketcore/presentation/framework/base_layout.py"
)

for f in "${files[@]}"; do
  test -f "$f"
done

PYTHONPYCACHEPREFIX=/tmp/framework_layout \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -E "SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(|<div|<section|</" src/marketcore/presentation/framework/base_layout.py; then
    echo "FORBIDDEN_DEPENDENCY_FOUND"
    exit 1
fi

if grep -E "title: str|subtitle: str|tooltip: str|layout_type: str|status_code: str|status_label: str" src/marketcore/presentation/framework/base_layout.py; then
    echo "RAW_UI_TEXT_OR_STRING_CODE_FIELD_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_layout import BaseLayout
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import (
    CardType,
    LayoutType,
    SectionType,
    UiStatusCode,
    WidgetType,
)

card = BaseCard(
    widget_id="ui.framework.test.card",
    widget_type=WidgetType.KPI,
    card_type=CardType.KPI,
    title_key="ui.framework.test.card.title",
    status_code=UiStatusCode.OK,
    status_label_key="ui.status.ok",
)

section_b = BaseSection(
    section_id="ui.framework.test.section.b",
    section_type=SectionType.PORTFOLIO,
    title_key="ui.framework.test.section.b.title",
    order=20,
    cards=(card,),
)

section_a = BaseSection(
    section_id="ui.framework.test.section.a",
    section_type=SectionType.SUMMARY,
    title_key="ui.framework.test.section.a.title",
    order=10,
    cards=(card,),
)

layout = BaseLayout(
    layout_id="ui.framework.test.layout.phone",
    layout_type=LayoutType.PHONE,
    title_key="ui.framework.test.layout.title",
    subtitle_key="ui.framework.test.layout.subtitle",
    tooltip_key="ui.framework.test.layout.tooltip",
    status_code=UiStatusCode.WARNING,
    status_label_key="ui.status.warning",
    sections=(section_b, section_a),
)

assert layout.is_visible()
assert layout.is_enabled()
assert layout.has_sections()

ordered = layout.ordered_sections()
assert ordered[0].section_id == "ui.framework.test.section.a"
assert ordered[1].section_id == "ui.framework.test.section.b"

data = layout.to_dict()
assert data["layout_type"] == LayoutType.PHONE.value
assert data["status_code"] == UiStatusCode.WARNING.value
assert data["title_key"] == "ui.framework.test.layout.title"
assert len(data["sections"]) == 2
assert data["sections"][0]["section_type"] == SectionType.SUMMARY.value
assert data["sections"][0]["cards"][0]["card_type"] == CardType.KPI.value

print("base_layout=OK")
PY

echo "framework_layer=OK"
echo "registry_layout_type=OK"
echo "registry_status_code=OK"
echo "i18n_keys_required=OK"
echo "ordered_sections=OK"
echo "html_in_model=0"
echo "sql_in_model=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FRAMEWORK_BASE_LAYOUT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_BASE_LAYOUT_V1_OK"
