from __future__ import annotations

from html import escape

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.framework.theme_model import ThemeModel
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1
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
) -> str:
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

    html = [
        f'<main class="mc-v2-shell" style="{escape(shell_style)}">',
        '<section class="mc-v2-page">',
        f'<h1>{escape(i18n.text(vm.title_key))}</h1>',
        f'<header class="mc-v2-header">{escape(i18n.text(vm.subtitle_key))}</header>',
    ]

    for section in vm.sections:
        html.append(
            f'<section class="mc-v2-section" data-section="{escape(section.section_type.value)}">'
        )
        html.append(f'<h2>{escape(i18n.text(section.title_key))}</h2>')
        html.append(f'<p>{escape(i18n.text(section.subtitle_key))}</p>')
        html.append(f'<div class="mc-v2-grid" style="{escape(grid_style)}">')

        for card in section.cards:
            html.append(
                "<article "
                f'class="mc-v2-card" '
                f'style="{escape(card_style)}" '
                f'data-card="{escape(card.card_type.value)}" '
                f'data-status="{escape(card.status_code.value)}">'
            )
            html.append(f'<h3>{escape(i18n.text(card.title_key))}</h3>')
            html.append(f'<div>{escape(i18n.text(card.subtitle_key))}</div>')

            values = card.payload.get("values", {})
            column_keys = card.payload.get("column_keys", {})

            if values:
                html.append('<dl class="mc-v2-values">')
                for column_name, raw_value in values.items():
                    column_key = str(column_keys.get(column_name, column_name))
                    html.append(
                        f'<div class="mc-v2-value-row" style="{escape(row_style)}">'
                        f"<dt>{escape(i18n.text(column_key))}</dt>"
                        f"<dd>{escape(formatter.value(str(column_name), raw_value))}</dd>"
                        "</div>"
                    )
                html.append("</dl>")

            html.append("</article>")

        html.append("</div>")
        html.append("</section>")

    html.append("</section>")
    html.append("</main>")

    return "\n".join(html)
