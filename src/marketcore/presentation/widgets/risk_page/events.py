from __future__ import annotations

from marketcore.presentation.design_system.components.timeline import TimelineCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.risk_control_center_vm import RiskControlCenterVM


class RiskEventsWidget:
    def render(self, vm: RiskControlCenterVM, lang: str = "ru") -> str:
        title = "События" if lang == "ru" else "Events"
        events = [
            {"time": x.time_label, "text": f"{x.event} — {x.level}"}
            for x in vm.events
        ]
        return SectionHeader(title) + DashboardGrid([TimelineCard(title, events)])
