from __future__ import annotations

from marketcore.presentation.components import (
    render_data_table,
    render_kpi_card,
    render_object_card,
    render_section,
)
from marketcore.presentation.components.discovery_action_panel import render_action_panel
from marketcore.presentation.page import Page
from marketcore.presentation.providers.discovery_control_provider import DiscoveryControlProvider


class DiscoveryControlPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-discovery",
            title="Discovery",
            icon="🔁",
            menu_order=15,
        )

    def render(self) -> str:
        vm = DiscoveryControlProvider().load()

        status = vm.status
        queue_total = sum(int(r.get("rows") or 0) for r in vm.queue)
        worker_done = sum(
            int(r.get("rows") or 0)
            for r in vm.worker
            if r.get("result_status") == "DONE"
        )
        worker_error = sum(
            int(r.get("rows") or 0)
            for r in vm.worker
            if r.get("result_status") == "ERROR"
        )

        kpi = "".join([
            render_kpi_card("Discovery", "ON" if status.get("enabled") else "OFF", f"profile={status.get('profile', '')}"),
            render_kpi_card("Interval", status.get("interval_minutes", ""), "minutes"),
            render_kpi_card("Queue", queue_total, "all statuses"),
            render_kpi_card("Worker OK", worker_done, f"errors={worker_error}"),
        ])

        scheduler_card = render_object_card("Scheduler", {
            "status": vm.scheduler.get("status", ""),
            "reason": vm.scheduler.get("reason", ""),
            "queued": vm.scheduler.get("queued_count", 0),
            "skipped": vm.scheduler.get("skipped_count", 0),
            "last": vm.scheduler.get("scheduler_ts", ""),
        })

        bottleneck_card = render_object_card("Bottleneck", {
            "stage": vm.bottleneck.get("pipeline_stage", ""),
            "conversion_pct": vm.bottleneck.get("conversion_pct", ""),
            "severity": vm.bottleneck.get("severity", ""),
            "root_cause": vm.bottleneck.get("root_cause_code", ""),
            "recommendation": vm.bottleneck.get("recommendation_code", ""),
            "expected_gain_pct": vm.bottleneck.get("expected_gain_pct", ""),
        })

        return (
            render_section("Discovery Loop", kpi)
            + render_section("Scheduler", scheduler_card)
            + render_section("Bottleneck", bottleneck_card)
            + render_section("Queue", render_data_table(["status", "rows"], vm.queue))
            + render_section("Worker", render_data_table(["result_status", "rows"], vm.worker))
            + render_section("Audit", render_data_table(["check_name", "result", "details", "audit_ts"], vm.audit))
            + render_section("Actions", render_action_panel(vm.actions))
            + render_section("Events", render_data_table(["event_code", "priority", "status", "expected_edge_gain", "created_at"], vm.events))
        )
