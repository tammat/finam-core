from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import HomeMetricVM


class ExecutionProvider:
    def load(self) -> list[HomeMetricVM]:
        return [
            HomeMetricVM("Выполн.", "Выкл.", "DISABLED", "Детали", "/execution"),
            HomeMetricVM("Micro", "Off", "DISABLED", "Детали", "/execution"),
            HomeMetricVM("Kill Switch", "READY", "READY", "Детали", "/execution"),
        ]

    def load_platform_metric(self) -> HomeMetricVM:
        return HomeMetricVM("Выполн.", "SAFE", "READY", "Детали", "/execution")
