from __future__ import annotations

from html import escape


def _v(value) -> str:
    return escape(str(value if value is not None else ""))


def _strategy_key(value) -> str:
    code = str(value if value is not None else "")
    return "strategy." + code.lower().replace("_", ".")

def _strategy_label(value) -> str:
    key = _strategy_key(value)
    return f'<span data-i18n-key="{_v(key)}">{_v(key)}</span>'


def render_edge_score_shadow_daily_card(vm: dict) -> str:
    rows = vm.get("rows") or []

    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{_v(row.get('trade_date'))}</td>"
            f"<td>{_v(row.get('symbol'))}</td>"
            f"<td>{_strategy_label(row.get('strategy_code'))}</td>"
            f"<td>{_v(row.get('timeframe'))}</td>"
            f"<td>{_v(row.get('observations_count'))}</td>"
            f"<td>{_v(row.get('runtime_seen_count'))}</td>"
            f"<td>{_v(row.get('signal_seen_count'))}</td>"
            f"<td>{_v(row.get('order_seen_count'))}</td>"
            f"<td>{_v(row.get('fill_seen_count'))}</td>"
            f"<td>{_v(row.get('avg_edge_score_v2'))}</td>"
            f"<td>{_v(row.get('min_edge_score_v2'))}</td>"
            f"<td>{_v(row.get('max_edge_score_v2'))}</td>"
            f"<td>{_v(row.get('pass_count'))}</td>"
            f"<td>{_v(row.get('review_count'))}</td>"
            "</tr>"
        )

    return f"""
    <div class="card edge-score-shadow-daily-card">
        <h2 data-i18n-key="edge.score.shadow.daily.title">edge.score.shadow.daily.title</h2>
        <div class="meta-row">
            <span data-i18n-key="edge.score.shadow.daily.readonly">edge.score.shadow.daily.readonly</span>
            <span>runtime_allowed={_v(vm.get("runtime_allowed"))}</span>
            <span>execution_allowed={_v(vm.get("execution_allowed"))}</span>
            <span>micro_live_allowed={_v(vm.get("micro_live_allowed"))}</span>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>trade_date</th>
                    <th>symbol</th>
                    <th>strategy</th>
                    <th>tf</th>
                    <th>observations</th>
                    <th>runtime_seen</th>
                    <th>signal_seen</th>
                    <th>order_seen</th>
                    <th>fill_seen</th>
                    <th>avg_score</th>
                    <th>min_score</th>
                    <th>max_score</th>
                    <th>pass</th>
                    <th>review</th>
                </tr>
            </thead>
            <tbody>
                {''.join(body)}
            </tbody>
        </table>
    </div>
    """
