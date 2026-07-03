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


class PaperSampleCollectionTimerHealthPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-sample-collection-timer-health",
            title="Paper Sample Collection Timer Health",
            icon="⚙",
            menu_order=23,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-sample-collection-timer-health")
        data = payload.get("data") or {}

        health = str(data.get("timer_health_status", "UNKNOWN"))
        timer_active = str(data.get("timer_active_state", "unknown"))
        service_result = str(data.get("service_result", "unknown"))
        age_sec = ctx.formatter.number(data.get("sample_summary_age_sec"), 0)
        candidates_total = ctx.formatter.number(data.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(data.get("sample_ready"), 0)

        return f"""
        <section class="card">
            <h2>Paper Sample Collection Timer Health</h2>
            <p>Контроль systemd timer/service и свежести sample collection summary.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_timer_health_v1.</p>
            <p><a href="/paper-sample-accumulation-monitor">← Paper Sample Accumulation Monitor</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Health", health, str(data.get("health_reason", "")))}
            {_metric("Timer", timer_active, str(data.get("timer_unit_file_state", "")))}
            {_metric("Service", service_result, str(data.get("service_active_state", "")))}
            {_metric("Age Sec", age_sec, "Возраст summary")}
            {_metric("Candidates", candidates_total, f"sample_ready={sample_ready}")}
        </div>

        <section class="card">
            <h2>Timer Details</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Timer Unit", str(data.get("timer_unit", "")))}
                    {_row("Timer Active State", str(data.get("timer_active_state", "")))}
                    {_row("Timer Sub State", str(data.get("timer_sub_state", "")))}
                    {_row("Timer Unit File State", str(data.get("timer_unit_file_state", "")))}
                    {_row("Next Elapse", str(data.get("timer_next_elapse", "")))}
                    {_row("Last Trigger", str(data.get("timer_last_trigger", "")))}
                    {_row("Timer Healthy", str(data.get("timer_healthy", "")))}
                    {_row("Service Unit", str(data.get("service_unit", "")))}
                    {_row("Service Active State", str(data.get("service_active_state", "")))}
                    {_row("Service Result", str(data.get("service_result", "")))}
                    {_row("Service Healthy", str(data.get("service_healthy", "")))}
                    {_row("Summary Exists", str(data.get("sample_summary_exists", "")))}
                    {_row("Summary Stale", str(data.get("sample_summary_stale", "")))}
                    {_row("Collection Status", str(data.get("collection_status", "")))}
                    {_row("Phase Status", str(data.get("phase_status", "")))}
                    {_row("Micro Live Allowed", str(data.get("micro_live_allowed", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1</p>
        </section>
        """
