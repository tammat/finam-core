from __future__ import annotations

from html import escape

from marketcore.presentation.localization import t


def _v(value) -> str:
    return escape(str(value if value is not None else ""))


def _strategy_key(value) -> str:
    code = str(value if value is not None else "")
    return "strategy." + code.lower().replace("_", ".")

def _strategy_label(value) -> str:
    key = _strategy_key(value)
    return f'<span data-i18n-key="{_v(key)}">{_v(key)}</span>'


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
            <div class="edge-score-explain-title" data-i18n-key="page.max_edge.explain.title">page.max_edge.explain.title</div>
            <table class="edge-score-explain-table">
                <thead>
                    <tr>
                        <th data-i18n-key="column.group">column.group</th>
                        <th data-i18n-key="column.score">column.score</th>
                        <th data-i18n-key="column.weight">column.weight</th>
                        <th data-i18n-key="column.contribution">column.contribution</th>
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
        <h2>{t("page.max_edge.title")}</h2>
        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-label">column.symbol</div><div class="kpi-value">{_v(current.get("symbol"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">column.strategy</div><div class="kpi-value">{_strategy_label(current.get("strategy_code"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">column.score</div><div class="kpi-value">{_v(current.get("edge_score"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">column.confidence</div><div class="kpi-value">{_v(current.get("confidence"))}</div></div>
        </div>
        <div class="meta-row">
            <span>column.timeframe {_v(current.get("timeframe"))}</span>
            <span>column.recommendation {_v(current.get("recommendation_code"))}</span>
            <span>column.trades {_v(current.get("trades"))}</span>
        </div>
        {render_edge_score_explain_card(current)}
    </div>
    """
