from __future__ import annotations

from marketcore.presentation.design_system.components.cards import MetricCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class MetadataSummaryWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        title = "Мета" if lang == "ru" else "Metadata"

        cards = [
            MetricCard(item.title, item.value, item.status)
            for item in vm.metadata
        ]

        return SectionHeader(title) + DashboardGrid(cards)
