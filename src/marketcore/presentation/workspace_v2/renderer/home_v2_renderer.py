from __future__ import annotations

from html import escape

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import HomeV2ViewModel


def render_home_v2(vm: HomeV2ViewModel, locale_code: str = "ru") -> str:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    layout = vm.layout

    html = [
        '<main class="mc-v2-shell">',
        '<section class="mc-v2-page">',
        f'<h1>{escape(i18n.text(layout.title_key))}</h1>',
        f'<header class="mc-v2-header">{escape(i18n.text(layout.subtitle_key))}</header>',
    ]

    for section in layout.ordered_sections():
        html.append(f'<section class="mc-v2-section" data-section="{escape(section.section_type.value)}">')
        html.append(f'<h2>{escape(i18n.text(section.title_key))}</h2>')
        html.append(f'<p>{escape(i18n.text(section.subtitle_key))}</p>')
        html.append('<div class="mc-v2-grid">')

        for card in section.ordered_cards():
            target = ""
            if card.actions:
                target = str(card.actions[0].get("target", ""))

            html.append(
                "<article "
                f'class="mc-v2-card" '
                f'data-card="{escape(card.card_type.value)}" '
                f'data-status="{escape(card.status_code.value)}">'
            )
            html.append(f'<h3>{escape(i18n.text(card.title_key))}</h3>')
            html.append(f'<div>{escape(i18n.text(card.subtitle_key))}</div>')

            if "rows_total" in card.payload:
                html.append(
                    f'<div>{escape(i18n.text("home.operator.rows"))}: '
                    f'{escape(str(card.payload["rows_total"]))}</div>'
                )

            if card.payload.get("updated_at"):
                html.append(
                    f'<div>{escape(i18n.text("home.operator.updated"))}: '
                    f'{escape(str(card.payload["updated_at"]))}</div>'
                )

            rows_total = card.payload.get("rows_total")
            updated_at = card.payload.get("updated_at")
            if rows_total is not None:
                html.append(
                    f'<div>{escape(i18n.text("home.card.status.rows"))}: {escape(str(rows_total))}</div>'
                )
            if updated_at:
                html.append(
                    f'<div>{escape(i18n.text("home.card.status.updated"))}: {escape(str(updated_at))}</div>'
                )

            if target:
                html.append(f'<a class="mc-v2-button" href="{escape(target)}">{escape(i18n.text("ui.action.open"))}</a>')
            html.append("</article>")

        html.append("</div>")
        html.append("</section>")

    html.append("</section>")
    html.append("</main>")

    return "\n".join(html)
