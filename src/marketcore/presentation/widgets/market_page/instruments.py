from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.market_intelligence_vm import MarketIntelligenceVM


class MarketInstrumentsWidget:
    def render(self, vm: MarketIntelligenceVM, lang: str = "ru") -> str:
        title = "Инструменты" if lang == "ru" else "Instruments"
        columns = ["Символ", "Класс", "Бары", "Дата", "Актуал.", "Статус"] if lang == "ru" else ["Symbol", "Class", "Bars", "Date", "Fresh", "Status"]
        rows = [[x.symbol, x.asset_class, x.bars, x.last_ts, x.freshness, x.status] for x in vm.instruments]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
