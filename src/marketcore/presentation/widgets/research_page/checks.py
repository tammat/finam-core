from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.research_center_vm import ResearchCenterVM


class ResearchChecksWidget:
    def render(self, vm: ResearchCenterVM, lang: str = "ru") -> str:
        title = "Проверки" if lang == "ru" else "Checks"
        columns = ["Проверка", "Результат", "Статус"] if lang == "ru" else ["Check", "Result", "Status"]
        rows = [[x.check, x.result, x.status] for x in vm.checks]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
