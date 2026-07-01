from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.execution_center_vm import ExecutionCenterVM


class ExecutionOrdersWidget:
    def render(self, vm: ExecutionCenterVM, lang: str = "ru") -> str:
        title = "Заявки" if lang == "ru" else "Orders"
        columns = ["Время", "Символ", "Сторона", "Кол-во", "Статус"] if lang == "ru" else ["Time", "Symbol", "Side", "Qty", "Status"]
        rows = [[x.time_label, x.symbol, x.side, x.qty, x.status] for x in vm.orders]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
