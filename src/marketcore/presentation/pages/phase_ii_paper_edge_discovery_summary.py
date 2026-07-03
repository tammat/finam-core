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


class PhaseIiPaperEdgeDiscoverySummaryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/phase-ii-paper-edge-discovery-summary",
            title="Phase II Paper Edge Discovery Summary",
            icon="✓",
            menu_order=25,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/phase-ii-paper-edge-discovery-summary")
        data = payload.get("data") or {}

        phase_result_status = str(data.get("phase_result_status", "UNKNOWN"))
        engineering_status = str(data.get("engineering_status", "UNKNOWN"))
        operational_status = str(data.get("operational_status", "UNKNOWN"))
        next_phase = str(data.get("next_phase", ""))

        return f"""
        <section class="card">
            <h2>Phase II Paper Edge Discovery Summary</h2>
            <p>Финальная сводка инженерной фазы Paper Edge Discovery и текущего операционного состояния.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.phase_ii_paper_edge_discovery_summary_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Phase Result", phase_result_status)}
            {_metric("Engineering", engineering_status)}
            {_metric("Operational", operational_status)}
            {_metric("Candidates", ctx.formatter.number(data.get("candidates_total"), 0))}
            {_metric("Micro Live Allowed", str(data.get("micro_live_allowed", False)))}
        </div>

        <section class="card">
            <h2>Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Phase Name", str(data.get("phase_name", "")))}
                    {_row("Phase Result Status", phase_result_status)}
                    {_row("Engineering Status", engineering_status)}
                    {_row("Operational Status", operational_status)}
                    {_row("Close Status", str(data.get("close_status", "")))}
                    {_row("Timer Health", str(data.get("timer_health_status", "")))}
                    {_row("Collection Status", str(data.get("collection_status", "")))}
                    {_row("Collection Phase Status", str(data.get("collection_phase_status", "")))}
                    {_row("Candidates Total", ctx.formatter.number(data.get("candidates_total"), 0))}
                    {_row("Sample Ready", ctx.formatter.number(data.get("sample_ready"), 0))}
                    {_row("Wait Both Sample", ctx.formatter.number(data.get("wait_both_sample"), 0))}
                    {_row("Min Remaining Total Trades", ctx.formatter.number(data.get("min_remaining_total_trades"), 0))}
                    {_row("Min Remaining OOS Trades", ctx.formatter.number(data.get("min_remaining_oos_trades"), 0))}
                    {_row("Average Progress", ctx.formatter.number(data.get("avg_progress_pct"), 2) + "%")}
                    {_row("Max Progress", ctx.formatter.number(data.get("max_progress_pct"), 2) + "%")}
                    {_row("Micro Live Ready Rows", ctx.formatter.number(data.get("micro_live_ready_rows"), 0))}
                    {_row("Micro Live Allowed Rows", ctx.formatter.number(data.get("micro_live_allowed_rows"), 0))}
                    {_row("Conclusion", str(data.get("conclusion", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Next Phase", next_phase)}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Pipeline Row Coverage</h2>
            <table>
                <thead>
                    <tr><th>Слой</th><th>Строк</th></tr>
                </thead>
                <tbody>
                    {_row("Research Candidates", ctx.formatter.number(data.get("paper_candidates_rows"), 0))}
                    {_row("Validation Queue", ctx.formatter.number(data.get("validation_queue_rows"), 0))}
                    {_row("Validation Pipeline", ctx.formatter.number(data.get("validation_pipeline_rows"), 0))}
                    {_row("Robustness", ctx.formatter.number(data.get("robustness_rows"), 0))}
                    {_row("OOS Validation", ctx.formatter.number(data.get("oos_validation_rows"), 0))}
                    {_row("OOS Backtest", ctx.formatter.number(data.get("oos_backtest_rows"), 0))}
                    {_row("Micro Live Readiness", ctx.formatter.number(data.get("micro_live_readiness_rows"), 0))}
                    {_row("Sample Monitor", ctx.formatter.number(data.get("sample_monitor_rows"), 0))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Result</h2>
            <p>PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1</p>
            <p><a href="/paper-sample-accumulation-monitor">Paper Sample Accumulation Monitor</a></p>
            <p><a href="/paper-runtime-sample-collection-phase-close">Phase Close</a></p>
        </section>
        """
