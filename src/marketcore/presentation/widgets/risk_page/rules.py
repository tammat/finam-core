from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.risk_control_center_vm import RiskControlCenterVM


class RiskRulesWidget:
    def render(self, vm: RiskControlCenterVM, lang: str = "ru") -> str:
        title = "Лимиты" if lang == "ru" else "Limits"
        columns = ["Правило", "Значение", "Лимит", "Статус", "Действие"] if lang == "ru" else ["Rule", "Value", "Limit", "Status", "Action"]
        rows = [[x.rule, x.value, x.limit, x.status, x.action] for x in vm.rules]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
