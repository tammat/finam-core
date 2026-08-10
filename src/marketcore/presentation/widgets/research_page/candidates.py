from __future__ import annotations

import html


class ResearchCandidatesWidget:
    def render(self, vm) -> str:
        rows = []

        for item in vm.candidates:
            values = (
                item.symbol,
                item.strategy,
                item.timeframe,
                item.trades,
                item.pnl,
                item.pf,
                item.status,
            )

            cells = "".join(
                f"<td>{html.escape(str(value))}</td>"
                for value in values
            )

            rows.append(
                f"<tr>{cells}</tr>"
            )

        if not rows:
            rows.append(
                '<tr><td colspan="7">Нет кандидатов.</td></tr>'
            )

        return (
            '<section class="fc-card">'
            '<h2>Кандидаты</h2>'
            '<div style="overflow-x:auto;">'
            '<table>'
            '<thead><tr>'
            '<th>Инструмент</th>'
            '<th>Стратегия</th>'
            '<th>TF</th>'
            '<th>Сделки</th>'
            '<th>PnL</th>'
            '<th>PF</th>'
            '<th>Статус</th>'
            '</tr></thead>'
            '<tbody>'
            + "".join(rows)
            + '</tbody>'
            '</table>'
            '</div>'
            '</section>'
        )
