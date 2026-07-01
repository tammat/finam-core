from __future__ import annotations

from marketcore.presentation.design_system.components.cards import MetricCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class PlatformStatusWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        title = "Платформа" if lang == "ru" else "Platform"

        cards = [
            MetricCard(item.title, item.value, item.status)
            for item in vm.platform
        ]

        return SectionHeader(title) + DashboardGrid(cards)
