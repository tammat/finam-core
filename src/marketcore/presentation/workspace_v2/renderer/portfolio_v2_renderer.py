from __future__ import annotations

from html import escape

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.workspace_v2.formatter.portfolio_v2_formatter import (
    PortfolioV2Formatter,
)
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import (
    PortfolioV2ViewModel,
)


def render_portfolio_v2(vm: PortfolioV2ViewModel, locale_code: str = "ru") -> str:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    formatter = PortfolioV2Formatter()

    html = [
        '<main class="mc-v2-shell">',
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
        html.append('<div class="mc-v2-grid">')

        for card in section.cards:
            html.append(
                "<article "
                f'class="mc-v2-card" '
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
                        "<div class=\"mc-v2-value-row\">"
                        f"<dt>{escape(i18n.text(column_key))}</dt>"
                        f"<dd>{escape(formatter.value(raw_value))}</dd>"
                        "</div>"
                    )
                html.append("</dl>")

            html.append("</article>")

        html.append("</div>")
        html.append("</section>")

    html.append("</section>")
    html.append("</main>")

    return "\n".join(html)
