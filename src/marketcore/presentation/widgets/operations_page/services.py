from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.operations_center_vm import OperationsCenterVM


class OperationsServicesWidget:
    def render(self, vm: OperationsCenterVM, lang: str = "ru") -> str:
        title = "Сервисы" if lang == "ru" else "Services"
        columns = ["Сервис", "Состояние", "Время работы", "Статус"] if lang == "ru" else ["Service", "State", "Uptime", "Status"]
        rows = [[x.service, x.state, x.uptime, x.status] for x in vm.services]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
