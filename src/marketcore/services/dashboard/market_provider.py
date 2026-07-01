from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import HomeMetricVM


class MarketProvider:
    def load(self) -> list[HomeMetricVM]:
        return [
            HomeMetricVM("Бары", "876K", "READY", "Рынок", "/market"),
            HomeMetricVM("Тики", "71M", "READY", "Рынок", "/market"),
            HomeMetricVM("Инстр.", "59", "READY", "Рынок", "/market"),
            HomeMetricVM("Fresh", "59", "READY", "Рынок", "/market"),
        ]
