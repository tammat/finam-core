#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

renderer="src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py"

test -f "$renderer"

PYTHONPYCACHEPREFIX=/tmp/marketcore_home_domain_render_tree_v2 \
PYTHONPATH=src \
python3 -m py_compile "$renderer"

if grep -nE 'ThemeResolver|UiI18nResolver|"class"|"style"|"href"|data-' "$renderer"
then
  echo "HOME_V2_PLATFORM_SEMANTIC_FOUND"
  exit 1
fi

PYTHONPATH=src python3 - <<'PY'
from datetime import datetime, timezone

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
from marketcore.presentation.render_tree.v2 import (
    render_document_v2_to_json,
    validate_render_document_v2,
)
from marketcore.presentation.workspace_v2.renderer.home_v2_domain_renderer import (
    render_home_domain_v2,
)
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import HomeV2ViewModel


as_of = datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc)
view_model = HomeV2ViewModel(
    layout=BaseLayout(
        layout_id="home.layout.desktop",
        layout_type=LayoutType.DESKTOP,
        title_key="home.workspace.title",
        subtitle_key="home.workspace.subtitle",
        status_code=UiStatusCode.WARNING,
        sections=(
            BaseSection(
                section_id="home.section.operating_traffic",
                section_type=SectionType.OBSERVATION,
                title_key="home.section.status.title",
                subtitle_key="home.section.status.subtitle",
                status_code=UiStatusCode.WARNING,
                cards=(
                    BaseCard(
                        widget_id="home.traffic.edge",
                        widget_type=WidgetType.STATUS,
                        card_type=CardType.ACTION,
                        title_key="home.card.edge.title",
                        subtitle_key="home.card.status.pending.subtitle",
                        status_code=UiStatusCode.BLOCKED,
                        actions=({"action_code": "OPEN", "target": "/legacy-engineering-route"},),
                        payload={"primary_value": 0, "updated_at": as_of},
                    ),
                    BaseCard(
                        widget_id="home.card.research",
                        widget_type=WidgetType.BASE,
                        card_type=CardType.ACTION,
                        title_key="home.card.research.title",
                        subtitle_key="ui.action.open",
                        status_code=UiStatusCode.WARNING,
                        payload={"availability": "UNAVAILABLE"},
                    ),
                ),
            ),
        ),
    )
)

document = render_home_domain_v2(view_model, generated_at=as_of)
validate_render_document_v2(
    document,
    message_keys={
        "home.workspace.title",
        "home.workspace.subtitle",
        "home.section.status.title",
        "home.section.status.subtitle",
        "home.card.edge.title",
        "home.card.status.pending.subtitle",
        "home.card.status.updated",
        "home.card.research.title",
        "ui.action.open",
    },
)
payload = render_document_v2_to_json(document)

assert '"schema_version":"marketcore.render_tree.v2"' in payload
assert '"timezone_code":"Europe/Moscow"' in payload
assert '"target_id":"container.edge"' in payload
assert "/legacy-engineering-route" not in payload
assert '"availability_code":"UNAVAILABLE"' in payload
assert '"class"' not in payload
assert '"style"' not in payload
assert '"href"' not in payload
assert 'data-' not in payload

print("home_v2_schema=OK")
print("home_message_keys=OK")
print("canonical_target_ids=OK")
print("legacy_urls_exported=0")
print("platform_semantics=0")
PY

echo "runtime_switch=0"
echo "service_restart=0"
echo "VERDICT=TEST_MARKETCORE_HOME_DOMAIN_RENDER_TREE_V2_OK"
