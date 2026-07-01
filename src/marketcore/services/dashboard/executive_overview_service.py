from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import (
    ExecutiveOverviewVM,
    HomeMetricVM,
)
from marketcore.services.dashboard.activity_provider import ActivityProvider
from marketcore.services.dashboard.execution_provider import ExecutionProvider
from marketcore.services.dashboard.market_provider import MarketProvider
from marketcore.services.dashboard.metadata_provider import MetadataProvider
from marketcore.services.dashboard.risk_provider import RiskProvider
from marketcore.services.dashboard.version_provider import VersionProvider


class ExecutiveOverviewService:
    def __init__(self) -> None:
        self.market_provider = MarketProvider()
        self.metadata_provider = MetadataProvider()
        self.risk_provider = RiskProvider()
        self.execution_provider = ExecutionProvider()
        self.version_provider = VersionProvider()
        self.activity_provider = ActivityProvider()

    def load(self) -> ExecutiveOverviewVM:
        market = self.market_provider.load()
        metadata = self.metadata_provider.load()
        execution = self.execution_provider.load()

        platform = [
            HomeMetricVM("Рынок", "READY", "READY", "Открыть", "/market"),
            HomeMetricVM("Исслед.", "READY", "READY", "Открыть", "/research"),
            HomeMetricVM("Мета", "100%", "READY", "Детали", "/metadata"),
            self.risk_provider.load_platform_metric(),
            self.execution_provider.load_platform_metric(),
            HomeMetricVM("Граф знаний", "Скоро", "DISABLED", "Детали", "#"),
        ]

        quick_actions = [
            HomeMetricVM("Диагн.", "Open", "INFO", "Открыть", "/system"),
            HomeMetricVM("Риски", "P1", "HIGH", "Открыть", "/risk"),
            HomeMetricVM("Рынок", "59", "READY", "Открыть", "/market"),
            HomeMetricVM("Исслед.", "Open", "READY", "Открыть", "/research"),
        ]

        return ExecutiveOverviewVM(
            title="Главная",
            product="MarketCore",
            subtitle="Trading Intelligence Platform",
            health_value="97%",
            health_status="READY",
            platform=platform,
            market=market,
            research=[
                HomeMetricVM("Replay", "READY", "READY", "Исслед.", "/research"),
                HomeMetricVM("OOS", "READY", "READY", "Исслед.", "/research"),
                HomeMetricVM("Edge", "READY", "READY", "Исслед.", "/research"),
            ],
            metadata=metadata,
            execution=execution,
            risk=self.risk_provider.load_risk(),
            version=self.version_provider.load(),
            activity=self.activity_provider.load(),
            quick_actions=quick_actions,
        )
