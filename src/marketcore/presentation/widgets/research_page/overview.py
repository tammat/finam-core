from __future__ import annotations

import html


class ResearchOverviewWidget:
    def render(self, vm) -> str:
        cards = []

        for item in vm.overview:
            status = html.escape(str(item.status))
            title = html.escape(str(item.title))
            value = html.escape(str(item.value))
            label = html.escape(str(item.action_label))
            href = html.escape(
                str(item.action_href),
                quote=True,
            )

            cards.append(
                '<div class="fc-card">'
                f'<div><b>{title}</b></div>'
                f'<div style="font-size:1.4rem;margin:8px 0;">{value}</div>'
                f'<div>Статус: {status}</div>'
                f'<div style="margin-top:8px;">'
                f'<a href="{href}">{label}</a>'
                '</div>'
                '</div>'
            )

        return (
            '<section class="fc-card">'
            '<h2>Обзор</h2>'
            '<div class="fc-grid">'
            + "".join(cards)
            + '</div>'
            '</section>'
        )
