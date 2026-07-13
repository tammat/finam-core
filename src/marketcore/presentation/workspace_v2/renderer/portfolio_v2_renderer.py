from __future__ import annotations

from marketcore.presentation.components.data_table_node import DataTableColumn, data_table_node
from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.framework.theme_model import ThemeModel
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1
from marketcore.presentation.render_tree.node_types import RenderNodeType
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.presentation.workspace_v2.formatter.portfolio_v2_formatter import (
    PortfolioV2Formatter,
)
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import (
    PortfolioV2ViewModel,
)
from marketcore.presentation.services.operator_settings_v1 import OperatorSettingsV1


def _theme_px(theme: ThemeModel, property_code: str) -> str:
    value = theme.get(property_code)

    if not value:
        raise RuntimeError(
            f"THEME_PROPERTY_NOT_FOUND:{property_code}"
        )

    return f"{int(value)}px"


def render_portfolio_v2(
    vm: PortfolioV2ViewModel,
    locale_code: str = "ru",
    theme_code: str = "DEFAULT",
    settings: OperatorSettingsV1 | None = None,
) -> RenderDocument:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    theme = ThemeResolverV1().resolve(theme_code)
    formatter = PortfolioV2Formatter(settings)

    shell_style = (
        f"max-width:{_theme_px(theme, 'SHELL_MAX_WIDTH')};"
        "margin:0 auto;"
        f"padding:{_theme_px(theme, 'SHELL_PADDING')};"
    )

    section_nodes: list[RenderNode] = []

    for section in vm.sections:
        ordered_columns: list[str] = []
        for card in section.cards:
            for column_name in card.payload.get("values", {}):
                if column_name not in ordered_columns:
                    ordered_columns.append(str(column_name))

        table_columns = [DataTableColumn("source", i18n.text("column.data_source"))]
        for column_name in ordered_columns:
            column_key = next(
                (
                    str(card.payload.get("column_keys", {}).get(column_name, column_name))
                    for card in section.cards
                    if column_name in card.payload.get("values", {})
                ),
                column_name,
            )
            table_columns.append(DataTableColumn(column_name, i18n.text(column_key)))

        table_rows = []
        for card in section.cards:
            values = card.payload.get("values", {})
            row = {"source": i18n.text(card.title_key)}
            row.update(
                {
                    column_name: formatter.value(column_name, values[column_name])
                    if column_name in values
                    else "—"
                    for column_name in ordered_columns
                }
            )
            table_rows.append(row)

        section_nodes.append(
            RenderNode(
                node_type=RenderNodeType.SECTION,
                props={
                    "class": "mc-v2-section",
                    "data-section": section.section_type.value,
                },
                children=(
                    RenderNode(
                        node_type=RenderNodeType.TITLE,
                        props={"level": 2},
                        text=i18n.text(section.title_key),
                    ),
                    RenderNode(
                        node_type=RenderNodeType.SUBTITLE,
                        text=i18n.text(section.subtitle_key),
                    ),
                    data_table_node(tuple(table_columns), tuple(table_rows)),
                ),
            )
        )

    return RenderDocument(
        root=RenderNode(
            node_type=RenderNodeType.WORKSPACE,
            props={
                "class": "mc-v2-shell",
                "style": shell_style,
            },
            children=(
                RenderNode(
                    node_type=RenderNodeType.PAGE,
                    props={"class": "mc-v2-page"},
                    children=(
                        RenderNode(
                            node_type=RenderNodeType.TITLE,
                            props={"level": 1},
                            text=i18n.text(vm.title_key),
                        ),
                        RenderNode(
                            node_type=RenderNodeType.HEADER,
                            props={"class": "mc-v2-header"},
                            text=i18n.text(vm.subtitle_key),
                        ),
                        *tuple(section_nodes),
                    ),
                ),
            ),
        )
    )
