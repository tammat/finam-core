from __future__ import annotations

import html


class ResearchActionsWidget:
    def render(self, vm) -> str:
        items = []

        for item in vm.actions:
            title = html.escape(str(item.title))
            value = html.escape(str(item.value))
            status = html.escape(str(item.status))
            label = html.escape(str(item.action_label))
            href = html.escape(
                str(item.action_href),
                quote=True,
            )

            items.append(
                '<div class="fc-card">'
                f'<b>{title}</b>'
                f'<div>{value}</div>'
                f'<div>Статус: {status}</div>'
                f'<div style="margin-top:8px;">'
                f'<a href="{href}">{label}</a>'
                '</div>'
                '</div>'
            )

        return (
            '<section class="fc-card">'
            '<h2>Действия</h2>'
            '<div class="fc-grid">'
            + "".join(items)
            + '</div>'
            '</section>'
        )
