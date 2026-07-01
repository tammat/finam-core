from __future__ import annotations

from marketcore.presentation.design_system.components.cards import KeyValueCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.formatters.status_formatter import StatusFormatter
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class RiskSummaryWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        title = "Риски" if lang == "ru" else "Risk"

        status = StatusFormatter.short(vm.risk.value, lang)

        card = KeyValueCard(
            title,
            {
                "Статус" if lang == "ru" else "Status": status,
                "Причина" if lang == "ru" else "Reason": vm.risk.reason,
                "Приоритет" if lang == "ru" else "Priority": vm.risk.priority,
                "Действие" if lang == "ru" else "Action": vm.risk.action_label,
            },
        )

        return SectionHeader(title) + DashboardGrid([card])
