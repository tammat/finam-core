from __future__ import annotations

import html


STATE_LABELS = {
    "TARGET_CANDIDATE": "TARGET",
    "NET_POSITIVE_BASELINE_INFERIOR": "NET+ / BASELINE−",
    "BASELINE_SUPERIOR_NET_NEGATIVE": "BASELINE+ / NET−",
    "NET_NEGATIVE_BASELINE_INFERIOR": "NET− / BASELINE−",
    "INSUFFICIENT_SAMPLE": "МАЛАЯ ВЫБОРКА",
}


class HomeEdgeSearchWidget:
    def render(self, frontier) -> str:
        rows: list[str] = []

        for item in frontier.rows[:3]:
            state = STATE_LABELS.get(
                str(item.state),
                str(item.state),
            )

            rows.append(
                '<div class="fc-row">'
                f'<b>#{html.escape(str(item.rank))} '
                f'{html.escape(str(item.physical_symbol))}</b>'
                f'<span>{html.escape(state)}</span>'
                f'<span>Net {html.escape(str(item.net_expectancy))}</span>'
                '</div>'
            )

        if not rows:
            rows.append(
                '<div class="fc-row">'
                'Нет кандидатов Edge Search.'
                '</div>'
            )

        return (
            '<section class="fc-card">'
            '<h2>Edge Search</h2>'
            '<p>'
            f'Статус: <b>{html.escape(str(frontier.status))}</b> · '
            f'Targets: <b>{html.escape(str(frontier.target_candidates))}</b>'
            '</p>'
            + "".join(rows)
            + '<p><a href="/research">Открыть Research Center</a></p>'
            '</section>'
        )
