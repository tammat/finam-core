from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class QuickActionsWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        title = "Быстрые действия" if lang == "ru" else "Quick Actions"

        cards = []

        for item in vm.quick_actions:
            cards.append(
                f"""
                <section class="fc-card">
                    <h3>{escape(item.title)}</h3>
                    <div class="fc-metric">{escape(item.value)}</div>
                    <a class="fc-nav-item" href="{escape(item.action_href)}">
                        {escape(item.action_label)} →
                    </a>
                </section>
                """
            )

        return SectionHeader(title) + DashboardGrid(cards)
