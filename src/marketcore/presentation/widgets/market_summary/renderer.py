from __future__ import annotations

from marketcore.presentation.design_system.components.cards import MetricCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class MarketSummaryWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        title = "Рынок" if lang == "ru" else "Market"

        cards = [
            MetricCard(item.title, item.value, item.status)
            for item in vm.market
        ]

        return SectionHeader(title) + DashboardGrid(cards)
