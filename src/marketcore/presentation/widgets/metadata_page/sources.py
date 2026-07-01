from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.metadata_center_vm import MetadataCenterVM


class MetadataSourcesWidget:
    def render(self, vm: MetadataCenterVM, lang: str = "ru") -> str:
        title = "Источники" if lang == "ru" else "Sources"
        columns = ["Источник", "Объекты", "Покрытие", "Статус"] if lang == "ru" else ["Source", "Objects", "Coverage", "Status"]
        rows = [[x.source, x.objects, x.coverage, x.status] for x in vm.sources]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
