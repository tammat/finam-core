from __future__ import annotations

from marketcore.presentation.design_system.components.timeline import TimelineCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class ActivitySummaryWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        title = "События" if lang == "ru" else "Activity"

        events = [
            {
                "time": item.time_label,
                "text": item.text,
            }
            for item in vm.activity[:5]
        ]

        return SectionHeader(title) + DashboardGrid(
            [
                TimelineCard(title, events),
            ]
        )
