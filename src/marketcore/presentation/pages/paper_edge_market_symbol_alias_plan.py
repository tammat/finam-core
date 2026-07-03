from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _metric(title: str, value: str, note: str = "") -> str:
    return f"""
    <section class="card">
        <h2>{escape(title)}</h2>
        <p style="font-size:28px;font-weight:700;margin:8px 0;">{escape(value)}</p>
        <p>{escape(note)}</p>
    </section>
    """


def _table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>План alias пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("plan_rank", "")))}</td>
            <td>{escape(str(row.get("candidate_symbol", "")))}</td>
            <td>{escape(str(row.get("candidate_root", "")))}</td>
            <td>{escape(str(row.get("candidate_strategy", "")))}</td>
            <td>{escape(str(row.get("candidate_timeframe", "")))}</td>
            <td>{escape(str(row.get("alias_symbol", "")))}</td>
            <td>{escape(str(row.get("alias_timeframe", "")))}</td>
            <td>{escape(str(row.get("alias_source_table", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("alias_bars_total"), 0))}</td>
            <td>{escape(ctx.formatter.datetime(row.get("alias_latest_bar_ts")))}</td>
            <td>{escape(ctx.formatter.number(row.get("alias_market_data_age_sec"), 0))}</td>
            <td>{escape(str(row.get("alias_match_type", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("alias_confidence"), 4))}</td>
            <td>{escape(str(row.get("alias_status", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Кандидат</th>
                <th>Root</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Alias Symbol</th>
                <th>Alias TF</th>
                <th>Источник</th>
                <th>Баров</th>
                <th>Последний бар</th>
                <th>Age sec</th>
                <th>Match</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeMarketSymbolAliasPlanPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-market-symbol-alias-plan",
            title="План alias рыночных символов",
            icon="◎",
            menu_order=23,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-edge-market-symbol-alias-plan?limit=100")
        rows = payload.get("data") or []

        strong = sum(1 for row in rows if row.get("alias_status") == "ALIAS_CANDIDATE_STRONG")
        weak = sum(1 for row in rows if row.get("alias_status") == "ALIAS_CANDIDATE_WEAK")
        missing = sum(1 for row in rows if row.get("alias_status") == "NO_ALIAS_FOUND")

        return f"""
        <section class="card">
            <h2>План alias рыночных символов</h2>
            <p>План предлагает соответствия между Paper-кандидатами и символами из market_bars.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_edge_market_symbol_alias_plan_v1.</p>
            <p><a href="/paper-edge-market-data-freshness">← Свежесть рыночных данных</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            {_metric("Всего строк", ctx.formatter.number(len(rows), 0))}
            {_metric("Strong Alias", ctx.formatter.number(strong, 0))}
            {_metric("Weak Alias", ctx.formatter.number(weak, 0))}
            {_metric("No Alias", ctx.formatter.number(missing, 0))}
        </div>

        <section class="card">
            <h2>Alias Plan</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Вывод</h2>
            <p>Сильные alias можно вынести в постоянный словарь соответствий. Слабые alias требуют ручной проверки.</p>
            <p>Следующий шаг: PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_APPLY_V1.</p>
        </section>
        """
