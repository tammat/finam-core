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
        return "<p>Привязка рыночных данных пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("binding_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("bars_source_table", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("bars_total"), 0))}</td>
            <td>{escape(ctx.formatter.datetime(row.get("latest_bar_ts")))}</td>
            <td>{escape(ctx.formatter.number(row.get("latest_close"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("market_data_age_sec"), 0))}</td>
            <td>{escape(str(row.get("market_data_status", "")))}</td>
            <td>{escape(str(row.get("binding_status", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Инструмент</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Источник</th>
                <th>Баров</th>
                <th>Последний бар</th>
                <th>Close</th>
                <th>Age sec</th>
                <th>Market Status</th>
                <th>Binding</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeMarketDataBindingPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-market-data-binding",
            title="Привязка рыночных данных",
            icon="◎",
            menu_order=21,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-edge-market-data-binding?limit=50")
        rows = payload.get("data") or []

        fresh = sum(1 for row in rows if row.get("market_data_status") == "FRESH_MARKET_DATA")
        stale = sum(1 for row in rows if row.get("market_data_status") == "STALE_MARKET_DATA")
        no_bars = sum(1 for row in rows if row.get("market_data_status") == "NO_BARS_FOR_CANDIDATE")
        no_source = sum(1 for row in rows if row.get("market_data_status") == "NO_MARKET_SOURCE")

        return f"""
        <section class="card">
            <h2>Привязка рыночных данных</h2>
            <p>Показывает, есть ли свежие market bars для кандидатов Paper Edge Discovery.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_edge_market_data_binding_v1.</p>
            <p><a href="/paper-edge-discovery">← Поиск преимущества</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Кандидатов", ctx.formatter.number(len(rows), 0))}
            {_metric("Fresh", ctx.formatter.number(fresh, 0))}
            {_metric("Stale", ctx.formatter.number(stale, 0))}
            {_metric("No Bars", ctx.formatter.number(no_bars, 0))}
            {_metric("No Source", ctx.formatter.number(no_source, 0))}
        </div>

        <section class="card">
            <h2>Market Data Binding</h2>
            {_table(rows, ctx)}
        </section>


        <section class="card">
            <h2>Freshness</h2>
            <p><a href="/paper-edge-market-data-freshness">Открыть диагностику свежести рыночных данных</a></p>
            <p>PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1</p>
        </section>

        <section class="card">
            <h2>Вывод</h2>
            <p>Если здесь STALE/NO_BARS/NO_SOURCE, значит Paper Edge Discovery пока опирается на накопленные paper/research данные, а не на свежий market feed.</p>
            <p>Следующий шаг: PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1.</p>
        </section>
        """
