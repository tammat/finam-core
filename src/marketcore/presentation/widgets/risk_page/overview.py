from __future__ import annotations

from marketcore.presentation.design_system.components.cards import MetricCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.risk_control_center_vm import RiskControlCenterVM


class RiskOverviewWidget:
    def render(self, vm: RiskControlCenterVM, lang: str = "ru") -> str:
        title = "Сводка" if lang == "ru" else "Overview"
        return SectionHeader(title) + DashboardGrid(
            [MetricCard(x.title, x.value, x.status) for x in vm.overview]
        )
