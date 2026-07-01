from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HomeMetricVM:
    title: str
    value: str
    status: str
    action_label: str = "Подробнее"
    action_href: str = "#"


@dataclass(frozen=True)
class HomeRiskVM:
    title: str = "Риски"
    value: str = "HIGH"
    reason: str = "Corr. risk"
    priority: str = "P1"
    action_label: str = "План P1"
    action_href: str = "/risk"


@dataclass(frozen=True)
class HomeVersionVM:
    product_name: str = "MarketCore"
    product_subtitle: str = "Trading Intelligence Platform"
    product_version: str = "1.0.0"
    dashboard_version: str = "1.0.0"
    repo: str = "finam-core"
    git_commit: str = "UNKNOWN"
    git_tag: str = "UNKNOWN"


@dataclass(frozen=True)
class HomeActivityVM:
    time_label: str
    text: str
    status: str = "READY"


@dataclass(frozen=True)
class ExecutiveOverviewVM:
    title: str = "Главная"
    product: str = "MarketCore"
    subtitle: str = "Trading Intelligence Platform"
    health_value: str = "97%"
    health_status: str = "READY"

    platform: list[HomeMetricVM] = field(default_factory=list)
    market: list[HomeMetricVM] = field(default_factory=list)
    research: list[HomeMetricVM] = field(default_factory=list)
    metadata: list[HomeMetricVM] = field(default_factory=list)
    execution: list[HomeMetricVM] = field(default_factory=list)

    risk: HomeRiskVM = field(default_factory=HomeRiskVM)
    version: HomeVersionVM = field(default_factory=HomeVersionVM)
    activity: list[HomeActivityVM] = field(default_factory=list)
    quick_actions: list[HomeMetricVM] = field(default_factory=list)


def build_default_executive_overview_vm() -> ExecutiveOverviewVM:
    return ExecutiveOverviewVM(
        platform=[
            HomeMetricVM("Рынок", "READY", "READY", "Открыть", "/market"),
            HomeMetricVM("Исслед.", "READY", "READY", "Открыть", "/research"),
            HomeMetricVM("Мета", "100%", "READY", "Детали", "/metadata"),
            HomeMetricVM("Риски", "HIGH", "HIGH", "План P1", "/risk"),
            HomeMetricVM("Выполн.", "SAFE", "READY", "Детали", "/execution"),
            HomeMetricVM("Граф знаний", "Скоро", "DISABLED", "Детали", "#"),
        ],
        market=[
            HomeMetricVM("Бары", "876K", "READY", "Рынок", "/market"),
            HomeMetricVM("Тики", "71M", "READY", "Рынок", "/market"),
            HomeMetricVM("Инстр.", "59", "READY", "Рынок", "/market"),
            HomeMetricVM("Fresh", "59", "READY", "Рынок", "/market"),
        ],
        research=[
            HomeMetricVM("Replay", "READY", "READY", "Исслед.", "/research"),
            HomeMetricVM("OOS", "READY", "READY", "Исслед.", "/research"),
            HomeMetricVM("Edge", "READY", "READY", "Исслед.", "/research"),
        ],
        metadata=[
            HomeMetricVM("Объекты", "373", "READY", "Мета", "/metadata"),
            HomeMetricVM("Источн.", "12", "READY", "Мета", "/metadata"),
            HomeMetricVM("Покрытие", "100%", "READY", "Мета", "/metadata"),
        ],
        execution=[
            HomeMetricVM("Выполн.", "Выкл.", "DISABLED", "Детали", "/execution"),
            HomeMetricVM("Micro", "Off", "DISABLED", "Детали", "/execution"),
            HomeMetricVM("Kill Switch", "READY", "READY", "Детали", "/execution"),
        ],
        activity=[
            HomeActivityVM("Now", "Base page ready"),
            HomeActivityVM("Now", "Component preview ready"),
            HomeActivityVM("Now", "Design system ready"),
        ],
        quick_actions=[
            HomeMetricVM("Диагн.", "Open", "INFO", "Открыть", "/system"),
            HomeMetricVM("Риски", "P1", "HIGH", "Открыть", "/risk"),
            HomeMetricVM("Рынок", "59", "READY", "Открыть", "/market"),
            HomeMetricVM("Исслед.", "Open", "READY", "Открыть", "/research"),
        ],
    )
