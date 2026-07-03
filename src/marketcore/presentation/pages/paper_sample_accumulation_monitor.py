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


def _row(label: str, value: str) -> str:
    return f"""
    <tr>
        <td>{escape(label)}</td>
        <td>{escape(value)}</td>
    </tr>
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

        summary_payload = ctx.api_get("/api/kg/v1/paper-runtime-sample-collection")
        monitor_payload = ctx.api_get("/api/kg/v1/paper-sample-accumulation-monitor?limit=50")

        summary = summary_payload.get("data") or {}
        rows = monitor_payload.get("data") or []

        candidates_total = ctx.formatter.number(summary.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(summary.get("sample_ready"), 0)
        wait_both = ctx.formatter.number(summary.get("wait_both_sample"), 0)
        min_total = ctx.formatter.number(summary.get("min_remaining_total_trades"), 0)
        min_oos = ctx.formatter.number(summary.get("min_remaining_oos_trades"), 0)
        avg_progress = ctx.formatter.number(summary.get("avg_progress_pct"), 2)
        max_progress = ctx.formatter.number(summary.get("max_progress_pct"), 2)
        collection_status = str(summary.get("collection_status", "UNKNOWN"))
        phase_status = str(summary.get("phase_status", "UNKNOWN"))
        recommended_action = str(summary.get("recommended_action", ""))
        refreshed_at = ctx.formatter.datetime(summary.get("refreshed_at"))

        ready = sum(1 for row in rows if row.get("sample_status") == "SAMPLE_READY")
        wait_total = sum(1 for row in rows if row.get("sample_status") == "WAIT_TOTAL_SAMPLE")
        wait_oos = sum(1 for row in rows if row.get("sample_status") == "WAIT_OOS_SAMPLE")

        return f"""
        <section class="card">
            <h2>Paper Sample Accumulation Monitor</h2>
            <p>Ответы на три вопроса: сколько Paper-сделок накоплено, сколько ещё нужно, какие кандидаты ближе всего к повторной проверке.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_v1 и marketcore_ui.paper_sample_accumulation_monitor_v1.</p>
            <p><a href="/paper-edge-discovery">← Paper Edge Discovery Center</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Кандидатов", candidates_total, "Всего в мониторинге")}
            {_metric("Ready", sample_ready, "Достаточная выборка")}
            {_metric("Wait Both", wait_both, "Не хватает общей и OOS-выборки")}
            {_metric("Need Total", min_total, "Минимально осталось общих сделок")}
            {_metric("Need OOS", min_oos, "Минимально осталось OOS-сделок")}
        </div>

        <section class="card">
            <h2>Sample Collection Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Collection Status", collection_status)}
                    {_row("Phase Status", phase_status)}
                    {_row("Average Progress", f"{avg_progress}%")}
                    {_row("Max Progress", f"{max_progress}%")}
                    {_row("Wait Total", ctx.formatter.number(wait_total, 0))}
                    {_row("Wait OOS", ctx.formatter.number(wait_oos, 0))}
                    {_row("Recommended Action", recommended_action)}
                    {_row("Refreshed At", refreshed_at)}
                    {_row("Source", "marketcore_ui.paper_runtime_sample_collection_v1")}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Closest Candidates To Recheck</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1</p>
        </section>
        """
