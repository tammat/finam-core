from __future__ import annotations

from html import escape


def _v(value) -> str:
    return escape(str(value if value is not None else ""))


def render_max_edge_card(current: dict) -> str:
    return f"""
    <div class="card max-edge-card">
        <h2>🎯 Максимальный edge</h2>
        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-label">Инструмент</div><div class="kpi-value">{_v(current.get("symbol"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">Стратегия</div><div class="kpi-value">{_v(current.get("strategy_code"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">Score</div><div class="kpi-value">{_v(current.get("edge_score"))}</div></div>
            <div class="kpi-card"><div class="kpi-label">Доверие</div><div class="kpi-value">{_v(current.get("confidence"))}</div></div>
        </div>
        <div class="meta-row">
            <span>TF: {_v(current.get("timeframe"))}</span>
            <span>Рекомендация: {_v(current.get("recommendation_code"))}</span>
            <span>Сделки: {_v(current.get("trades"))}</span>
        </div>
    </div>
    """
