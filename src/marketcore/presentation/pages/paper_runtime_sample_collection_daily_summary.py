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


class PaperRuntimeSampleCollectionDailySummaryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-runtime-sample-collection-daily-summary",
            title="Paper Runtime Sample Collection Daily Summary",
            icon="□",
            menu_order=28,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-sample-operations-daily-summary")
        data = payload.get("data") or {}

        daily_status = str(data.get("daily_status", "UNKNOWN"))
        operational_status = str(data.get("operational_status", "UNKNOWN"))
        operations_health = str(data.get("operations_health_status", "UNKNOWN"))

        return f"""
        <section class="card">
            <h2>Paper Runtime Sample Collection Daily Summary</h2>
            <p>Ежедневная сводка по операционному накоплению Paper/OOS выборки.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Daily Status", daily_status)}
            {_metric("Operational", operational_status)}
            {_metric("Operations Health", operations_health)}
            {_metric("Candidates", ctx.formatter.number(data.get("candidates_total"), 0))}
            {_metric("Micro Live Allowed", str(data.get("micro_live_allowed", False)))}
        </div>

        <section class="card">
            <h2>Daily Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Summary Date", str(data.get("summary_date", "")))}
                    {_row("Phase Result", str(data.get("phase_result_status", "")))}
                    {_row("Engineering", str(data.get("engineering_status", "")))}
                    {_row("Operational", operational_status)}
                    {_row("Phase Close", str(data.get("phase_close_status", "")))}
                    {_row("Timer Health", str(data.get("timer_health_status", "")))}
                    {_row("Operations Health", operations_health)}
                    {_row("Operations Rows", ctx.formatter.number(data.get("operations_rows"), 0))}
                    {_row("Operations High Rows", ctx.formatter.number(data.get("operations_high_rows"), 0))}
                    {_row("Operations Near Ready Rows", ctx.formatter.number(data.get("operations_near_ready_rows"), 0))}
                    {_row("Operations Collecting Rows", ctx.formatter.number(data.get("operations_collecting_rows"), 0))}
                    {_row("Candidates Total", ctx.formatter.number(data.get("candidates_total"), 0))}
                    {_row("Sample Ready", ctx.formatter.number(data.get("sample_ready"), 0))}
                    {_row("Wait Both Sample", ctx.formatter.number(data.get("wait_both_sample"), 0))}
                    {_row("Average Progress", ctx.formatter.number(data.get("avg_progress_pct"), 2) + "%")}
                    {_row("Max Progress", ctx.formatter.number(data.get("max_progress_pct"), 2) + "%")}
                    {_row("Min Remaining Total Trades", ctx.formatter.number(data.get("min_remaining_total_trades"), 0))}
                    {_row("Min Remaining OOS Trades", ctx.formatter.number(data.get("min_remaining_oos_trades"), 0))}
                    {_row("Micro Live Allowed Rows", ctx.formatter.number(data.get("micro_live_allowed_rows"), 0))}
                    {_row("Conclusion", str(data.get("conclusion", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Навигация</h2>
            <p><a href="/risk">Риски</a></p>
            <p><a href="/settings">Настройки</a></p>
            <p><a href="/paper-runtime-sample-collection-operations">Operations Queue</a></p>
            <p><a href="/paper-sample-operations-timer-health">Operations Timer Health</a></p>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1</p>
        </section>
        """
