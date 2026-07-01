from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.execution_center_vm import ExecutionCenterVM


class ExecutionFillsWidget:
    def render(self, vm: ExecutionCenterVM, lang: str = "ru") -> str:
        title = "Сделки" if lang == "ru" else "Fills"
        columns = ["Время", "Символ", "Кол-во", "Цена", "Статус"] if lang == "ru" else ["Time", "Symbol", "Qty", "Price", "Status"]
        rows = [[x.time_label, x.symbol, x.qty, x.price, x.status] for x in vm.fills]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
