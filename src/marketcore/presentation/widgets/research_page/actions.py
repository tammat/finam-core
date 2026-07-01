from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.research_center_vm import ResearchCenterVM


class ResearchActionsWidget:
    def render(self, vm: ResearchCenterVM, lang: str = "ru") -> str:
        title = "Действия" if lang == "ru" else "Actions"
        cards = []
        for x in vm.actions:
            cards.append(
                f'<section class="fc-card"><h3>{escape(x.title)}</h3>'
                f'<div class="fc-metric">{escape(x.value)}</div>'
                f'<a class="fc-nav-item" href="{escape(x.action_href)}">{escape(x.action_label)} →</a></section>'
            )
        return SectionHeader(title) + DashboardGrid(cards)
