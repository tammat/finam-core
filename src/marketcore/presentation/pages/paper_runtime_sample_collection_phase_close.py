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


class PaperRuntimeSampleCollectionPhaseClosePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-runtime-sample-collection-phase-close",
            title="Paper Runtime Sample Collection Phase Close",
            icon="✓",
            menu_order=24,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-runtime-sample-collection-phase-close")
        data = payload.get("data") or {}

        engineering_status = str(data.get("engineering_status", "UNKNOWN"))
        operational_status = str(data.get("operational_status", "UNKNOWN"))
        close_status = str(data.get("close_status", "UNKNOWN"))
        next_phase = str(data.get("next_phase", ""))

        candidates_total = ctx.formatter.number(data.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(data.get("sample_ready"), 0)
        wait_both = ctx.formatter.number(data.get("wait_both_sample"), 0)
        min_total = ctx.formatter.number(data.get("min_remaining_total_trades"), 0)
        min_oos = ctx.formatter.number(data.get("min_remaining_oos_trades"), 0)

        return f"""
        <section class="card">
            <h2>Paper Runtime Sample Collection Phase Close</h2>
            <p>Фиксация завершения инженерной фазы Paper Edge Discovery / Sample Collection.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_phase_close_v1.</p>
            <p><a href="/paper-sample-accumulation-monitor">← Sample Monitor</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Engineering", engineering_status)}
            {_metric("Operational", operational_status)}
            {_metric("Close", close_status)}
            {_metric("Candidates", candidates_total)}
            {_metric("Sample Ready", sample_ready)}
        </div>

        <section class="card">
            <h2>Phase Close Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Phase Name", str(data.get("phase_name", "")))}
                    {_row("Engineering Status", engineering_status)}
                    {_row("Operational Status", operational_status)}
                    {_row("Close Status", close_status)}
                    {_row("Close Reason", str(data.get("close_reason", "")))}
                    {_row("Candidates Total", candidates_total)}
                    {_row("Sample Ready", sample_ready)}
                    {_row("Wait Both Sample", wait_both)}
                    {_row("Min Remaining Total Trades", min_total)}
                    {_row("Min Remaining OOS Trades", min_oos)}
                    {_row("Timer Health", str(data.get("timer_health_status", "")))}
                    {_row("Timer Healthy", str(data.get("timer_healthy", "")))}
                    {_row("Service Healthy", str(data.get("service_healthy", "")))}
                    {_row("Summary Stale", str(data.get("sample_summary_stale", "")))}
                    {_row("Micro Live Ready Rows", ctx.formatter.number(data.get("micro_live_ready_rows"), 0))}
                    {_row("Micro Live Allowed Rows", ctx.formatter.number(data.get("micro_live_allowed_rows"), 0))}
                    {_row("Micro Live Allowed", str(data.get("micro_live_allowed", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Next Phase", next_phase)}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Result</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1</p>
            <p>Текущая фаза закрыта как инженерный контур. Операционный статус зависит от накопления Paper/OOS выборки.</p>
        </section>
        """
