from __future__ import annotations

from html import escape

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1
from marketcore.presentation.workspace_v2.formatter.portfolio_v2_formatter import (
    PortfolioV2Formatter,
)
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import (
    PortfolioV2ViewModel,
)


def _px(value: str) -> str:
    return f"{int(value)}px"


def render_portfolio_v2(vm: PortfolioV2ViewModel, locale_code: str = "ru") -> str:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    theme = ThemeResolverV1().resolve("DEFAULT")
    formatter = PortfolioV2Formatter()

    shell_style = (
        f"max-width:{_px(theme.get('SHELL_MAX_WIDTH', '1600'))};"
        "margin:0 auto;"
        f"padding:{_px(theme.get('SHELL_PADDING', '12'))};"
    )

    grid_style = (
        "display:grid;"
        f"grid-template-columns:repeat(auto-fit,minmax({_px(theme.get('GRID_MIN_CARD_WIDTH', '340'))},1fr));"
        f"gap:{_px(theme.get('GRID_GAP', '12'))};"
    )

    card_style = (
        f"border-radius:{_px(theme.get('CARD_RADIUS', '18'))};"
        f"padding:{_px(theme.get('CARD_PADDING', '14'))};"
    )

    row_style = (
        "display:grid;"
        "grid-template-columns:1fr auto;"
        f"gap:{_px(theme.get('VALUE_ROW_GAP', '8'))};"
    )

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
