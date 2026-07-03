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
        return "<p>Sample Accumulation Monitor пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("monitor_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("sample_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("progress_pct"), 2))}%</td>
            <td>{escape(ctx.formatter.number(row.get("total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_oos_trades"), 0))}</td>
            <td>{escape(str(row.get("readiness_status", "")))}</td>
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
                <th>Sample Status</th>
                <th>Progress</th>
                <th>Total Trades</th>
                <th>Need Total</th>
                <th>OOS Trades</th>
                <th>Need OOS</th>
                <th>Readiness</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperSampleAccumulationMonitorPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-sample-accumulation-monitor",
            title="Paper Sample Accumulation Monitor",
            icon="□",
            menu_order=22,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-sample-accumulation-monitor?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("sample_status") == "SAMPLE_READY")
        wait_both = sum(1 for row in rows if row.get("sample_status") == "WAIT_BOTH_SAMPLE")
        wait_total = sum(1 for row in rows if row.get("sample_status") == "WAIT_TOTAL_SAMPLE")
        wait_oos = sum(1 for row in rows if row.get("sample_status") == "WAIT_OOS_SAMPLE")

        return f"""
        <section class="card">
            <h2>Paper Sample Accumulation Monitor</h2>
            <p>Монитор показывает, сколько paper-сделок и OOS-сделок осталось накопить до Micro Live readiness.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_sample_accumulation_monitor_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready", ctx.formatter.number(ready, 0))}
            {_metric("Wait Both", ctx.formatter.number(wait_both, 0))}
            {_metric("Wait Total", ctx.formatter.number(wait_total, 0))}
            {_metric("Wait OOS", ctx.formatter.number(wait_oos, 0))}
        </div>

        <section class="card">
            <h2>Accumulation</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_V1</p>
        </section>
        """
