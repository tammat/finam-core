from __future__ import annotations

from marketcore.presentation.design_system.components.cards import MetricCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.metadata_center_vm import MetadataCenterVM


class MetadataOverviewWidget:
    def render(self, vm: MetadataCenterVM, lang: str = "ru") -> str:
        title = "Сводка" if lang == "ru" else "Overview"
        return SectionHeader(title) + DashboardGrid(
            [MetricCard(x.title, x.value, x.status) for x in vm.overview]
        )
