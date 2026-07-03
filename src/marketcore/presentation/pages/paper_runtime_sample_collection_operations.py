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
        return "<p>Operations пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("operation_rank", "")))}</td>
            <td>{escape(str(row.get("operation_priority", "")))}</td>
            <td>{escape(str(row.get("operation_status", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("sample_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("progress_pct"), 2))}%</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_oos_trades"), 0))}</td>
            <td>{escape(str(row.get("operation_reason", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
            <td>{escape(str(row.get("next_check", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Инструмент</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Sample</th>
                <th>Progress</th>
                <th>Need Total</th>
                <th>Need OOS</th>
                <th>Причина</th>
                <th>Действие</th>
                <th>Next Check</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperRuntimeSampleCollectionOperationsPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-runtime-sample-collection-operations",
            title="Paper Runtime Sample Collection Operations",
            icon="□",
            menu_order=26,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-runtime-sample-collection-operations?limit=50")
        rows = payload.get("data") or []

        high = sum(1 for row in rows if row.get("operation_priority") == "HIGH")
        normal = sum(1 for row in rows if row.get("operation_priority") == "NORMAL")
        collecting = sum(1 for row in rows if row.get("operation_status") == "COLLECTING")
        near = sum(1 for row in rows if row.get("operation_status") == "NEAR_SAMPLE_READY")
        allowed = sum(1 for row in rows if row.get("micro_live_allowed") is True)

        return f"""
        <section class="card">
            <h2>Paper Runtime Sample Collection Operations</h2>
            <p>Ежедневная операционная очередь: что делать с кандидатами, ожидающими накопления Paper/OOS выборки.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_operations_v1.</p>
            <p><a href="/phase-ii-paper-edge-discovery-summary">← Phase II Summary</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("High", ctx.formatter.number(high, 0))}
            {_metric("Normal", ctx.formatter.number(normal, 0))}
            {_metric("Collecting", ctx.formatter.number(collecting, 0))}
            {_metric("Near Ready", ctx.formatter.number(near, 0))}
        </div>

        <section class="card">
            <h2>Safety</h2>
            <p>micro_live_allowed_rows={escape(ctx.formatter.number(allowed, 0))}</p>
        </section>

        <section class="card">
            <h2>Operations Queue</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_V1</p>
        </section>
        """
