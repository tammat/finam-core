from __future__ import annotations

from marketcore.presentation.design_system.components.cards import MetricCard
from marketcore.presentation.formatters.status_formatter import StatusFormatter
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class ExecutiveHealthWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        status_label = StatusFormatter.short(vm.health_status, lang)
        return MetricCard(
            title="Система" if lang == "ru" else "System",
            value=vm.health_value,
            status=vm.health_status,
        ) + f'<div class="fc-card"><strong>{status_label}</strong><br><a href="/system">Подробнее →</a></div>'
