from __future__ import annotations

from html import escape

from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import (
    PortfolioV2ViewModel,
)


def render_portfolio_v2(vm: PortfolioV2ViewModel) -> str:

    html = [
        '<main class="mc-v2-shell">',
        f'<section class="mc-v2-page" data-i18n-key="{escape(vm.title_key)}">',
        f'<header class="mc-v2-header" data-i18n-key="{escape(vm.subtitle_key)}"></header>',
    ]

    for section in vm.sections:

        html.append(
            f'<section class="mc-v2-section" '
            f'data-section="{escape(section.section_type.value)}">'
        )

        html.append(
            f'<h2 data-i18n-key="{escape(section.title_key)}"></h2>'
        )

        html.append(
            f'<div class="mc-v2-grid">'
        )

        for card in section.cards:

            html.append(
                "<article "
                f'class="mc-v2-card" '
                f'data-card="{escape(card.card_type.value)}" '
                f'data-status="{escape(card.status_code.value)}">'
            )

            html.append(
                f'<h3 data-i18n-key="{escape(card.title_key)}"></h3>'
            )

            html.append(
                f'<div data-i18n-key="{escape(card.subtitle_key)}"></div>'
            )

            html.append("</article>")

        html.append("</div>")
        html.append("</section>")

    html.append("</section>")
    html.append("</main>")

    return "\n".join(html)
