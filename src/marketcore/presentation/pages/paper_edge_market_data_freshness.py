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
        return "<p>Freshness-диагностика пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("freshness_rank", "")))}</td>
            <td>{escape(str(row.get("row_type", "")))}</td>
            <td>{escape(str(row.get("candidate_symbol", "")))}</td>
            <td>{escape(str(row.get("market_symbol", "")))}</td>
            <td>{escape(str(row.get("market_timeframe", "")))}</td>
            <td>{escape(str(row.get("source_table", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("bars_total"), 0))}</td>
            <td>{escape(ctx.formatter.datetime(row.get("latest_bar_ts")))}</td>
            <td>{escape(ctx.formatter.number(row.get("latest_close"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("market_data_age_sec"), 0))}</td>
            <td>{escape(str(row.get("freshness_status", "")))}</td>
            <td>{escape(str(row.get("diagnosis", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Тип</th>
                <th>Кандидат</th>
                <th>Market Symbol</th>
                <th>TF</th>
                <th>Источник</th>
                <th>Баров</th>
                <th>Последний бар</th>
                <th>Close</th>
                <th>Age sec</th>
                <th>Status</th>
                <th>Диагноз</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeMarketDataFreshnessPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-market-data-freshness",
            title="Свежесть рыночных данных",
            icon="◎",
            menu_order=22,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-edge-market-data-freshness?limit=100")
        rows = payload.get("data") or []

        candidate_no_bars = sum(1 for row in rows if row.get("freshness_status") == "CANDIDATE_NO_BARS")
        source_fresh = sum(1 for row in rows if row.get("freshness_status") == "SOURCE_FRESH")
        source_stale = sum(1 for row in rows if row.get("freshness_status") == "SOURCE_STALE")
        no_source = sum(1 for row in rows if row.get("freshness_status") == "NO_MARKET_SOURCE")

        return f"""
        <section class="card">
            <h2>Свежесть рыночных данных</h2>
            <p>Диагностика показывает две вещи: есть ли свежий market feed вообще и совпадают ли Paper-кандидаты с market_bars.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_edge_market_data_freshness_v1.</p>
            <p><a href="/paper-edge-market-data-binding">← Привязка рыночных данных</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего строк", ctx.formatter.number(len(rows), 0))}
            {_metric("Candidate No Bars", ctx.formatter.number(candidate_no_bars, 0))}
            {_metric("Source Fresh", ctx.formatter.number(source_fresh, 0))}
            {_metric("Source Stale", ctx.formatter.number(source_stale, 0))}
            {_metric("No Source", ctx.formatter.number(no_source, 0))}
        </div>

        <section class="card">
            <h2>Freshness Matrix</h2>
            {_table(rows, ctx)}
        </section>


        <section class="card">
            <h2>Alias Plan</h2>
            <p><a href="/paper-edge-market-symbol-alias-plan">Открыть план alias рыночных символов</a></p>
            <p>PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1</p>
        </section>

        <section class="card">
            <h2>Вывод</h2>
            <p>Если SOURCE_FRESH есть, но CANDIDATE_NO_BARS=20, проблема не в отсутствии market feed, а в несовпадении символов/timeframe кандидатов и market_bars.</p>
            <p>Следующий шаг: PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1.</p>
        </section>
        """
