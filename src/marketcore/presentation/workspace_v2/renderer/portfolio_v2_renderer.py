from __future__ import annotations

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.framework.theme_model import ThemeModel
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.presentation.workspace_v2.formatter.portfolio_v2_formatter import (
    PortfolioV2Formatter,
)
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import (
    PortfolioV2ViewModel,
)


def _theme_px(theme: ThemeModel, property_code: str) -> str:
    value = theme.get(property_code)
    if not value:
        raise RuntimeError(f"THEME_PROPERTY_NOT_FOUND:{property_code}")
    return f"{int(value)}px"


def _value_row_layout(theme: ThemeModel) -> str:
    layout = theme.get("VALUE_ROW_LAYOUT", "INLINE")
    if layout == "STACKED":
        return "display:grid;grid-template-columns:1fr;gap:" + _theme_px(theme, "VALUE_ROW_GAP") + ";"
    return "display:grid;grid-template-columns:1fr auto;gap:" + _theme_px(theme, "VALUE_ROW_GAP") + ";"


def render_portfolio_v2(
    vm: PortfolioV2ViewModel,
    locale_code: str = "ru",
    theme_code: str = "DEFAULT",
) -> RenderDocument:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    theme = ThemeResolverV1().resolve(theme_code)
    formatter = PortfolioV2Formatter()

    shell_style = (
        f"max-width:{_theme_px(theme, 'SHELL_MAX_WIDTH')};"
        "margin:0 auto;"
        f"padding:{_theme_px(theme, 'SHELL_PADDING')};"
    )

    grid_style = (
        "display:grid;"
        f"grid-template-columns:repeat(auto-fit,minmax({_theme_px(theme, 'GRID_MIN_CARD_WIDTH')},1fr));"
        f"gap:{_theme_px(theme, 'GRID_GAP')};"
    )

    card_style = (
        f"border-radius:{_theme_px(theme, 'CARD_RADIUS')};"
        f"padding:{_theme_px(theme, 'CARD_PADDING')};"
    )

    row_style = _value_row_layout(theme)

    section_nodes = []

    for section in vm.sections:
        card_nodes = []

        for card in section.cards:
            value_nodes = []
            values = card.payload.get("values", {})
            column_keys = card.payload.get("column_keys", {})

            for column_name, raw_value in values.items():
                column_key = str(column_keys.get(column_name, column_name))
                value_nodes.append(
                    RenderNode(
                        "div",
                        props={"class": "mc-v2-value-row", "style": row_style},
                        children=(
                            RenderNode("dt", text=i18n.text(column_key)),
                            RenderNode("dd", text=formatter.value(str(column_name), raw_value)),
                        ),
                    )
                )

            children = [
                RenderNode("h3", text=i18n.text(card.title_key)),
                RenderNode("div", text=i18n.text(card.subtitle_key)),
            ]

            if value_nodes:
                children.append(
                    RenderNode(
                        "dl",
                        props={"class": "mc-v2-values"},
                        children=tuple(value_nodes),
                    )
                )

            card_nodes.append(
                RenderNode(
                    "article",
                    props={
                        "class": "mc-v2-card",
                        "style": card_style,
                        "data-card": card.card_type.value,
                        "data-status": card.status_code.value,
                    },
                    children=tuple(children),
                )
            )

        section_nodes.append(
            RenderNode(
                "section",
                props={"class": "mc-v2-section", "data-section": section.section_type.value},
                children=(
                    RenderNode("h2", text=i18n.text(section.title_key)),
                    RenderNode("p", text=i18n.text(section.subtitle_key)),
                    RenderNode(
                        "div",
                        props={"class": "mc-v2-grid", "style": grid_style},
                        children=tuple(card_nodes),
                    ),
                ),
            )
        )

    return RenderDocument(
        root=RenderNode(
            "main",
            props={"class": "mc-v2-shell", "style": shell_style},
            children=(
                RenderNode(
                    "section",
                    props={"class": "mc-v2-page"},
                    children=(
                        RenderNode("h1", text=i18n.text(vm.title_key)),
                        RenderNode("header", props={"class": "mc-v2-header"}, text=i18n.text(vm.subtitle_key)),
                        *tuple(section_nodes),
                    ),
                ),
            ),
        )
    )
