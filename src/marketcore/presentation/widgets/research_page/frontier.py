from __future__ import annotations

import html


STATE_LABELS = {
    "TARGET_CANDIDATE": "TARGET",
    "NET_POSITIVE_BASELINE_INFERIOR": "NET+ / BASELINE−",
    "BASELINE_SUPERIOR_NET_NEGATIVE": "BASELINE+ / NET−",
    "NET_NEGATIVE_BASELINE_INFERIOR": "NET− / BASELINE−",
    "INSUFFICIENT_SAMPLE": "МАЛАЯ ВЫБОРКА",
}


class ResearchFrontierWidget:
    def render(self, vm) -> str:
        frontier = vm.frontier

        rows = []

        for item in frontier.rows:
            state = STATE_LABELS.get(
                str(item.state),
                str(item.state),
            )

            values = (
                item.rank,
                item.physical_symbol,
                item.strategy,
                item.side,
                state,
                f"{item.pairs}/{item.oos_pairs}",
                item.net_expectancy,
                item.paired_gain,
                item.placebo_delta,
            )

            cells = "".join(
                f"<td>{html.escape(str(value))}</td>"
                for value in values
            )

            rows.append(f"<tr>{cells}</tr>")

        if not rows:
            rows.append(
                '<tr><td colspan="9">'
                'Нет данных Edge Search.'
                '</td></tr>'
            )

        status = html.escape(str(frontier.status))
        targets = html.escape(
            str(frontier.target_candidates)
        )
        cohorts = html.escape(
            str(frontier.physical_cohorts)
        )

        return (
            '<section class="fc-card">'
            '<h2>Edge Search</h2>'
            '<p>'
            f'Статус: <b>{status}</b> · '
            f'Target candidates: <b>{targets}</b> · '
            f'Physical cohorts: <b>{cohorts}</b>'
            '</p>'
            '<p>'
            'Рейтинг read-only. '
            'Не разрешает execution или micro-live.'
            '</p>'
            '<div style="overflow-x:auto;">'
            '<table>'
            '<thead><tr>'
            '<th>#</th>'
            '<th>Контракт</th>'
            '<th>Стратегия</th>'
            '<th>Side</th>'
            '<th>State</th>'
            '<th>Pairs/OOS</th>'
            '<th>Net</th>'
            '<th>Paired gain</th>'
            '<th>Placebo Δ</th>'
            '</tr></thead>'
            '<tbody>'
            + "".join(rows)
            + '</tbody>'
            '</table>'
            '</div>'
            '</section>'
        )
