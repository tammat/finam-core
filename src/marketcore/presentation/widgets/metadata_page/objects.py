from __future__ import annotations

from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.metadata_center_vm import MetadataCenterVM


class MetadataObjectsWidget:
    def render(self, vm: MetadataCenterVM, lang: str = "ru") -> str:
        title = "Объекты" if lang == "ru" else "Objects"
        columns = ["Объект", "Слой", "Строк", "Качество", "Статус"] if lang == "ru" else ["Object", "Layer", "Rows", "Quality", "Status"]
        rows = [[x.name, x.layer, x.rows_count, x.quality, x.status] for x in vm.objects]
        return SectionHeader(title) + DashboardGrid([TableCard(title, columns, rows)])
