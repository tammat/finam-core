from __future__ import annotations

from html import escape


def _v(value) -> str:
    return escape(str(value if value is not None else ""))


def render_edge_score_shadow_observation_card(vm: dict) -> str:
    rows = vm.get("rows") or []

    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{_v(row.get('observed_at'))}</td>"
            f"<td>{_v(row.get('symbol'))}</td>"
            f"<td>{_v(row.get('strategy_code'))}</td>"
            f"<td>{_v(row.get('timeframe'))}</td>"
            f"<td>{_v(row.get('edge_score_v2'))}</td>"
            f"<td>{_v(row.get('model_verdict'))}</td>"
            f"<td>{_v(row.get('reconciliation_verdict'))}</td>"
            f"<td>{_v(row.get('runtime_seen'))}</td>"
            f"<td>{_v(row.get('signal_seen'))}</td>"
            f"<td>{_v(row.get('order_seen'))}</td>"
            f"<td>{_v(row.get('fill_seen'))}</td>"
            f"<td>{_v(row.get('observation_status'))}</td>"
            "</tr>"
        )

    return f"""
    <div class="card edge-score-shadow-observation-card">
        <h2 data-i18n-key="edge.score.shadow.title">edge.score.shadow.title</h2>
        <div class="meta-row">
            <span data-i18n-key="edge.score.shadow.readonly">edge.score.shadow.readonly</span>
            <span>runtime_allowed={_v(vm.get("runtime_allowed"))}</span>
            <span>execution_allowed={_v(vm.get("execution_allowed"))}</span>
            <span>micro_live_allowed={_v(vm.get("micro_live_allowed"))}</span>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>observed_at</th>
                    <th>symbol</th>
                    <th>strategy</th>
                    <th>tf</th>
                    <th>score_v2</th>
                    <th>model</th>
                    <th>reconciliation</th>
                    <th>runtime_seen</th>
                    <th>signal_seen</th>
                    <th>order_seen</th>
                    <th>fill_seen</th>
                    <th>status</th>
                </tr>
            </thead>
            <tbody>
                {''.join(body)}
            </tbody>
        </table>
    </div>
    """
