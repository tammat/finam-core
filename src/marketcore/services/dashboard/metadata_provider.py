from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import HomeMetricVM


class MetadataProvider:
    def load(self) -> list[HomeMetricVM]:
        return [
            HomeMetricVM("Объекты", "373", "READY", "Мета", "/metadata"),
            HomeMetricVM("Источн.", "12", "READY", "Мета", "/metadata"),
            HomeMetricVM("Покрытие", "100%", "READY", "Мета", "/metadata"),
        ]
