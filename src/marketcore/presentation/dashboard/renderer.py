from __future__ import annotations

from marketcore.presentation.components.common.html import h
from marketcore.presentation.components.widgets.button import render_button
from marketcore.presentation.components.widgets.badge import render_badge
from marketcore.presentation.components.cards import render_kpi_card
from marketcore.presentation.dashboard.viewmodel import DashboardViewModel


FORBIDDEN_ACTION_TYPES = {"execution", "order", "live", "broker"}


def _label(key: str) -> str:
    return f'<span data-i18n-key="{h(key)}">{h(key)}</span>'


def _render_toolbar(vm: DashboardViewModel) -> str:
    items = []
    for item in vm.toolbar:
        if item.action_type in FORBIDDEN_ACTION_TYPES:
            continue
        items.append(render_button(item.label_key, item.href, item.icon, item.disabled))
    return f'<div class="ui-toolbar dashboard-toolbar">{"".join(items)}</div>'


def _render_kpis(vm: DashboardViewModel) -> str:
    cards = []
    for kpi in vm.kpis:
        cards.append(render_kpi_card(kpi.label_key, kpi.value, kpi.hint_key))
    return f'<div class="kpi-grid dashboard-kpis">{"".join(cards)}</div>'


def _render_alerts(vm: DashboardViewModel) -> str:
    alerts = vm.alerts[:5]
    body = "".join(render_badge(alert.message_key, alert.tone) for alert in alerts)
    return f'<div class="dashboard-alerts">{body}</div>'


def _render_table(vm: DashboardViewModel) -> str:
    header = "".join(
        f'<th data-i18n-key="{h(col.label_key)}">{h(col.label_key)}</th>'
        for col in vm.table.columns
    )
    rows = []
    for row in vm.table.rows:
        cells = "".join(f"<td>{h(row.get(col.key))}</td>" for col in vm.table.columns)
        rows.append(f"<tr>{cells}</tr>")

    if not rows:
        rows.append(
            f'<tr><td colspan="{len(vm.table.columns)}" data-i18n-key="{h(vm.table.empty_message_key)}">'
            f'{h(vm.table.empty_message_key)}</td></tr>'
        )

    return f"""
    <table class="data-table ui-data-table dashboard-table">
        <thead><tr>{header}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
    </table>
    """


def _assert_read_only(vm: DashboardViewModel) -> None:
    safety = vm.safety
    if (
        safety.runtime_allowed != 0
        or safety.execution_allowed != 0
        or safety.micro_live_allowed != 0
        or safety.orders_changed != 0
        or safety.fills_changed != 0
    ):
        raise ValueError("DASHBOARD_SAFETY_VIOLATION")


def render_dashboard(vm: DashboardViewModel) -> str:
    _assert_read_only(vm)

    return f"""
    <section class="dashboard" data-dashboard-id="{h(vm.dashboard_id)}">
        <header class="dashboard-header">
            <div class="dashboard-title-row">
                <span class="dashboard-icon">{h(vm.icon)}</span>
                <h1 data-i18n-key="{h(vm.title_key)}">{h(vm.title_key)}</h1>
            </div>
            <p data-i18n-key="{h(vm.subtitle_key)}">{h(vm.subtitle_key)}</p>
            <div class="dashboard-updated">{h(vm.updated_at)}</div>
        </header>
        {_render_toolbar(vm)}
        {_render_alerts(vm)}
        {_render_kpis(vm)}
        {_render_table(vm)}
        <footer class="dashboard-footer">
            <span>runtime_allowed={h(vm.safety.runtime_allowed)}</span>
            <span>execution_allowed={h(vm.safety.execution_allowed)}</span>
            <span>micro_live_allowed={h(vm.safety.micro_live_allowed)}</span>
        </footer>
    </section>
    """
