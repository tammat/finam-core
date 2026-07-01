from __future__ import annotations

from marketcore.presentation.design_system.components.timeline import TimelineCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.operations_center_vm import OperationsCenterVM


class OperationsEventsWidget:
    def render(self, vm: OperationsCenterVM, lang: str = "ru") -> str:
        title = "События" if lang == "ru" else "Events"
        events = [
            {"time": x.time_label, "text": f"{x.event} — {x.level}"}
            for x in vm.events
        ]
        return SectionHeader(title) + DashboardGrid([TimelineCard(title, events)])
