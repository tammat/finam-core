from __future__ import annotations

from html import escape


def _v(value) -> str:
    return escape(str(value if value is not None else ""))


def render_edge_score_explain_card(current: dict) -> str:
    groups = current.get("edge_score_explain_groups") or []
    if not groups:
        return ""

    rows = []
    for group in groups:
        rows.append(
            "<tr>"
            f"<td>{_v(group.get('group_code'))}</td>"
            f"<td>{_v(group.get('group_score'))}</td>"
            f"<td>{_v(group.get('group_weight'))}</td>"
            f"<td>{_v(group.get('group_contribution'))}</td>"
            "</tr>"
        )

    return f"""
        <div class="edge-score-explain-card" data-i18n-scope="edge.score.explain">
            <div class="edge-score-explain-title" data-i18n-key="edge.score.explain.title">edge.score.explain.title</div>
            <table class="edge-score-explain-table">
                <thead>
                    <tr>
                        <th data-i18n-key="edge.score.explain.group">edge.score.explain.group</th>
                        <th data-i18n-key="edge.score.explain.score">edge.score.explain.score</th>
                        <th data-i18n-key="edge.score.explain.weight">edge.score.explain.weight</th>
                        <th data-i18n-key="edge.score.explain.contribution">edge.score.explain.contribution</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
    """


def render_max_edge_card(current: dict) -> str:
    return f"""
    <div class="card max-edge-card">
        <h2>edge.score.max.title</h2>
        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-label">edge.score.max.symbol</div><div class="kpi-value">{_v(current.get("symbol"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">edge.score.max.strategy</div><div class="kpi-value">{_v(current.get("strategy_code"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">edge.score.max.score</div><div class="kpi-value">{_v(current.get("edge_score"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">edge.score.max.confidence</div><div class="kpi-value">{_v(current.get("confidence"))}</div></div>
        </div>
        <div class="meta-row">
            <span>edge.score.max.timeframe {_v(current.get("timeframe"))}</span>
            <span>edge.score.max.recommendation {_v(current.get("recommendation_code"))}</span>
            <span>edge.score.max.trades {_v(current.get("trades"))}</span>
        </div>
        {render_edge_score_explain_card(current)}
    </div>
    """
