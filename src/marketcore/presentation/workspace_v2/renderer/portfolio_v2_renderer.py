from __future__ import annotations

from numbers import Number

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


def _value_row_layout(theme: ThemeModel) -> str:
    layout = theme.get("VALUE_ROW_LAYOUT", "INLINE")
    gap = _theme_px(theme, "VALUE_ROW_GAP")

    if layout == "STACKED":
        return (
            "display:grid;"
            "grid-template-columns:1fr;"
            f"gap:{gap};"
        )

    return (
        "display:grid;"
        "grid-template-columns:1fr auto;"
        f"gap:{gap};"
    )


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

    grid_style = (
        "display:grid;"
        "grid-template-columns:"
        "repeat(auto-fit,minmax("
        f"{_theme_px(theme, 'GRID_MIN_CARD_WIDTH')},1fr));"
        f"gap:{_theme_px(theme, 'GRID_GAP')};"
    )

    card_style = (
        f"border-radius:{_theme_px(theme, 'CARD_RADIUS')};"
        f"padding:{_theme_px(theme, 'CARD_PADDING')};"
    )

    row_style = _value_row_layout(theme)
    section_nodes: list[RenderNode] = []

    for section in vm.sections:
        card_nodes: list[RenderNode] = []

        for card in section.cards:
            value_nodes: list[RenderNode] = []
            values = card.payload.get("values", {})
            column_keys = card.payload.get("column_keys", {})

            for column_name, raw_value in values.items():
                column_key = str(
                    column_keys.get(column_name, column_name)
                )

                value_class = "mc-v2-metric-value"
                if "p&l" in str(column_name).lower() and isinstance(raw_value, Number):
                    if raw_value < 0:
                        value_class += " is-negative"
                    elif raw_value > 0:
                        value_class += " is-positive"

                value_nodes.append(
                    RenderNode(
                        node_type=RenderNodeType.METRIC_ROW,
                        props={
                            "class": "mc-v2-value-row",
                            "style": row_style,
                        },
                        children=(
                            RenderNode(
                                node_type=RenderNodeType.METRIC_LABEL,
                                text=i18n.text(column_key),
                            ),
                            RenderNode(
                                node_type=RenderNodeType.METRIC_VALUE,
                                props={"class": value_class},
                                text=formatter.value(
                                    str(column_name),
                                    raw_value,
                                ),
                            ),
                        ),
                    )
                )

            card_children: list[RenderNode] = [
                RenderNode(
                    node_type=RenderNodeType.TITLE,
                    props={"level": 3},
                    text=i18n.text(card.title_key),
                ),
                RenderNode(
                    node_type=RenderNodeType.TEXT,
                    text=i18n.text(card.subtitle_key),
                ),
            ]

            if value_nodes:
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.METRIC_LIST,
                        props={"class": "mc-v2-values"},
                        children=tuple(value_nodes),
                    )
                )

            card_nodes.append(
                RenderNode(
                    node_type=RenderNodeType.CARD,
                    props={
                        "class": "mc-v2-card",
                        "style": card_style,
                        "data-card": card.card_type.value,
                        "data-status": card.status_code.value,
                    },
                    children=tuple(card_children),
                )
            )

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
                    RenderNode(
                        node_type=RenderNodeType.GRID,
                        props={
                            "class": "mc-v2-grid",
                            "style": grid_style,
                        },
                        children=tuple(card_nodes),
                    ),
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
