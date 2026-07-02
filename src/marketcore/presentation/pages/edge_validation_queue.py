from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Очередь Edge Validation пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("queue_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("validation_status", "")))}</td>
            <td>{escape(str(row.get("priority", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("trades"), 0))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
            <td>{escape(str(row.get("risk_notes", "")))}</td>
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
                <th>Статус</th>
                <th>Priority</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>Trades</th>
                <th>Действие</th>
                <th>Риски</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeValidationQueuePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-validation-queue",
            title="Edge Validation Queue",
            icon="✓",
            menu_order=16,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-validation-queue?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("validation_status") == "READY_FOR_EDGE_VALIDATION")
        watchlist = sum(1 for row in rows if row.get("validation_status") == "WATCHLIST")
        low_sample = sum(1 for row in rows if row.get("validation_status") == "ACCUMULATE_SAMPLE")

        return f"""
        <section class="card">
            <h2>Edge Validation Queue</h2>
            <p>Очередь кандидатов, которые должны пройти следующую проверку перед продвижением к Paper/Micro Live.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_validation_queue_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            <section class="card"><h2>Всего</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(len(rows), 0))}</p></section>
            <section class="card"><h2>Ready</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(ready, 0))}</p></section>
            <section class="card"><h2>Watchlist</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(watchlist, 0))}</p></section>
            <section class="card"><h2>Low Sample</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(low_sample, 0))}</p></section>
        </div>

        <section class="card">
            <h2>Queue</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_VALIDATION_PIPELINE_V1</p>
        </section>
        """
