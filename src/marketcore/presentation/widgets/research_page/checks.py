from __future__ import annotations

import html


class ResearchChecksWidget:
    def render(self, vm) -> str:
        rows = []

        for item in vm.checks:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.check))}</td>"
                f"<td>{html.escape(str(item.result))}</td>"
                f"<td>{html.escape(str(item.status))}</td>"
                "</tr>"
            )

        if not rows:
            rows.append(
                '<tr><td colspan="3">Нет проверок.</td></tr>'
            )

        return (
            '<section class="fc-card">'
            '<h2>Проверки</h2>'
            '<table>'
            '<thead><tr>'
            '<th>Проверка</th>'
            '<th>Результат</th>'
            '<th>Статус</th>'
            '</tr></thead>'
            '<tbody>'
            + "".join(rows)
            + '</tbody>'
            '</table>'
            '</section>'
        )
