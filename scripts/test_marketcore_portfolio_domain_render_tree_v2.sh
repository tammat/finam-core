#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

renderer="src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_domain_renderer.py"

test -f "$renderer"

PYTHONPYCACHEPREFIX=/tmp/marketcore_portfolio_domain_render_tree_v2 \
PYTHONPATH=src \
python3 -m py_compile "$renderer"

if grep -nE 'ThemeResolver|UiI18nResolver|PortfolioV2Formatter|"class"|"style"|"href"|data-' "$renderer"
then
  echo "PORTFOLIO_V2_PLATFORM_SEMANTIC_FOUND"
  exit 1
fi

PYTHONPATH=src python3 - <<'PY'
from datetime import datetime, timezone
from decimal import Decimal

from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import CardType, SectionType, UiStatusCode, WidgetType
from marketcore.presentation.render_tree.v2 import render_document_v2_to_json, validate_render_document_v2
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_domain_renderer import render_portfolio_domain_v2
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import PortfolioV2ViewModel


as_of = datetime(2026, 7, 15, 15, 30, tzinfo=timezone.utc)
view_model = PortfolioV2ViewModel(
    title_key="portfolio.workspace.title",
    subtitle_key="portfolio.workspace.subtitle",
    sections=(
        BaseSection(
            section_id="portfolio.section.summary",
            section_type=SectionType.SUMMARY,
            title_key="portfolio.section.summary.title",
            subtitle_key="portfolio.section.summary.subtitle",
            status_code=UiStatusCode.OK,
            cards=(
                BaseCard(
                    widget_id="portfolio.card.summary.1",
                    widget_type=WidgetType.BASE,
                    card_type=CardType.BASE,
                    title_key="portfolio.source.summary",
                    status_code=UiStatusCode.OK,
                    payload={
                        "source_view": "portfolio.summary_v1",
                        "values": {
                            "Equity": Decimal("100000.25"),
                            "P&L %": Decimal("1.25"),
                            "Updated At": as_of,
                        },
                        "column_keys": {
                            "Equity": "portfolio.column.equity",
                            "P&L %": "portfolio.column.pnl_pct",
                            "Updated At": "portfolio.column.updated_at",
                        },
                    },
                ),
            ),
        ),
    ),
)

document = render_portfolio_domain_v2(view_model, generated_at=as_of)
validate_render_document_v2(document, message_keys={
    "portfolio.workspace.title",
    "portfolio.workspace.subtitle",
    "portfolio.section.summary.title",
    "portfolio.section.summary.subtitle",
    "column.data_source",
    "portfolio.source.summary",
    "portfolio.column.equity",
    "portfolio.column.pnl_pct",
    "portfolio.column.updated_at",
})
payload = render_document_v2_to_json(document)

assert '"format_code":"MONEY_RUB"' in payload
assert '"format_code":"PERCENT"' in payload
assert '"format_code":"DATETIME"' in payload
assert '"source_identity":"portfolio.summary_v1"' in payload
assert '100 000' not in payload
assert "₽" not in payload
assert '"class"' not in payload
assert '"style"' not in payload
assert '"href"' not in payload

print("portfolio_v2_schema=OK")
print("raw_values=OK")
print("format_codes=OK")
print("source_lineage=OK")
print("platform_semantics=0")
PY

echo "runtime_switch=0"
echo "service_restart=0"
echo "VERDICT=TEST_MARKETCORE_PORTFOLIO_DOMAIN_RENDER_TREE_V2_OK"
