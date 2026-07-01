from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.research_center_vm import ResearchCenterVM


class ResearchCandidatesWidget:
    def render(self, vm: ResearchCenterVM, lang: str = "ru") -> str:
        title = "Кандидаты" if lang == "ru" else "Candidates"
        columns = ["Символ", "Стратегия", "ТФ", "Сделки", "PnL", "PF", "Статус"] if lang == "ru" else ["Symbol", "Strategy", "TF", "Trades", "PnL", "PF", "Status"]
        rows = [[x.symbol, x.strategy, x.timeframe, x.trades, x.pnl, x.pf, x.status] for x in vm.candidates]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
