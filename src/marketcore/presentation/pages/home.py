from __future__ import annotations

from html import escape

from marketcore.presentation.api_client import get_json
from marketcore.presentation.page import Page


def _status_badge(status: str) -> str:
    status = status or "UNKNOWN"
    return f'<span class="badge">{escape(status)}</span>'


class HomePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/",
            title="MarketCore OS",
            icon="⌂",
            menu_order=10,
        )

    def render(self) -> str:
        kg_health = get_json("/api/kg/v1/health")
        kg_stats = get_json("/api/kg/v1/statistics")
        kg_validation = get_json("/api/kg/v1/validation")

        health_status = kg_health.get("status", "ERROR")
        health_data = kg_health.get("data") or {}
        stats_rows = kg_stats.get("data") or []
        validation_rows = kg_validation.get("data") or []

        nodes = health_data.get("nodes", "—")

        stats_html = ""
        for row in stats_rows:
            stats_html += f"""
            <tr>
                <td>{escape(str(row.get("domain", "")))}</td>
                <td>{escape(str(row.get("nodes", "")))}</td>
                <td>{escape(str(row.get("edges", "")))}</td>
                <td>{escape(str(row.get("entity_types", "")))}</td>
                <td>{escape(str(row.get("edge_types", "")))}</td>
            </tr>
            """

        validation_html = ""
        for row in validation_rows:
            validation_html += f"""
            <tr>
                <td>{escape(str(row.get("domain", "")))}</td>
                <td>{_status_badge(str(row.get("status", "")))}</td>
                <td>{escape(str(row.get("total_findings", "")))}</td>
                <td>{escape(str(row.get("finished_at", "")))}</td>
            </tr>
            """

        if not stats_html:
            stats_html = '<tr><td colspan="5">Нет данных Knowledge Graph API.</td></tr>'

        if not validation_html:
            validation_html = '<tr><td colspan="4">Нет данных Validation API.</td></tr>'

        return f"""
        <section class="card">
            <h2>Platform M2</h2>
            <p>MarketCore OS активен. UI Shell работает через единый registry и layout.</p>
        </section>

        <section class="card">
            <h2>Knowledge Graph API</h2>
            <p>Статус: {_status_badge(health_status)}</p>
            <p>Узлов в графе: <strong>{escape(str(nodes))}</strong></p>
        </section>

        <section class="card">
            <h2>Knowledge Graph Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Домен</th>
                        <th>Узлы</th>
                        <th>Связи</th>
                        <th>Типы сущностей</th>
                        <th>Типы связей</th>
                    </tr>
                </thead>
                <tbody>{stats_html}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Validation</h2>
            <table>
                <thead>
                    <tr>
                        <th>Домен</th>
                        <th>Статус</th>
                        <th>Findings</th>
                        <th>Завершено</th>
                    </tr>
                </thead>
                <tbody>{validation_html}</tbody>
            </table>
        </section>
        """
