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


class MarketcoreUiSystemdHealthPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/marketcore-ui-systemd-health",
            title="MarketCore UI Systemd Health",
            icon="⚙",
            menu_order=121,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/marketcore-ui-systemd-health")
        data = payload.get("data") or {}

        overall = str(data.get("overall_status", "UNKNOWN"))
        kg = str(data.get("kg_api_health_status", "UNKNOWN"))
        ui = str(data.get("ui_shell_health_status", "UNKNOWN"))

        return f"""
        <section class="card">
            <h2>MarketCore UI Systemd Health</h2>
            <p>Контроль KG API на 8095 и MarketCore UI Shell на 8080.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.marketcore_ui_systemd_8080_health_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Overall", overall)}
            {_metric("KG API", kg, str(data.get("kg_api_active_state", "")))}
            {_metric("UI Shell", ui, str(data.get("ui_shell_active_state", "")))}
            {_metric("8080", str(data.get("ui_home_http_ok", "")), str(data.get("open_url", "")))}
            {_metric("Safety", "OK" if data.get("micro_live_allowed") in {False, 0, None} else "ERROR", "micro_live_allowed=0")}
        </div>

        <section class="card">
            <h2>Systemd Details</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("KG API Unit", str(data.get("kg_api_unit", "")))}
                    {_row("KG API Active", str(data.get("kg_api_active_state", "")))}
                    {_row("KG API Result", str(data.get("kg_api_result", "")))}
                    {_row("KG API HTTP OK", str(data.get("kg_api_http_ok", "")))}
                    {_row("UI Shell Unit", str(data.get("ui_shell_unit", "")))}
                    {_row("UI Shell Active", str(data.get("ui_shell_active_state", "")))}
                    {_row("UI Shell Result", str(data.get("ui_shell_result", "")))}
                    {_row("Home HTTP OK", str(data.get("ui_home_http_ok", "")))}
                    {_row("Risk HTTP OK", str(data.get("ui_risk_http_ok", "")))}
                    {_row("Settings HTTP OK", str(data.get("ui_settings_http_ok", "")))}
                    {_row("Open URL", str(data.get("open_url", "")))}
                    {_row("Risk URL", str(data.get("risk_url", "")))}
                    {_row("Settings URL", str(data.get("settings_url", "")))}
                    {_row("Health Reason", str(data.get("health_reason", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1</p>
        </section>
        """
