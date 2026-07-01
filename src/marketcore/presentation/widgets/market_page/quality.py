from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.market_intelligence_vm import MarketIntelligenceVM


class MarketQualityWidget:
    def render(self, vm: MarketIntelligenceVM, lang: str = "ru") -> str:
        title = "Качество" if lang == "ru" else "Quality"
        columns = ["Проверка", "Объект", "Строк", "Ошибок", "Статус"] if lang == "ru" else ["Check", "Object", "Rows", "Bad", "Status"]
        rows = [[x.check, x.object_name, x.rows_checked, x.bad_rows, x.status] for x in vm.quality]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
