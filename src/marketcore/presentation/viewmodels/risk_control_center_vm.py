from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskMetricVM:
    title: str
    value: str
    status: str
    action_label: str = "Подробнее"
    action_href: str = "#"


@dataclass(frozen=True)
class RiskRuleVM:
    rule: str
    value: str
    limit: str
    status: str
    action: str


@dataclass(frozen=True)
class RiskEventVM:
    time_label: str
    event: str
    level: str
    status: str


@dataclass(frozen=True)
class RiskControlCenterVM:
    title: str = "Риски"
    subtitle: str = "Risk Control Center"

    overview: list[RiskMetricVM] = field(default_factory=list)
    rules: list[RiskRuleVM] = field(default_factory=list)
    events: list[RiskEventVM] = field(default_factory=list)
    actions: list[RiskMetricVM] = field(default_factory=list)


def build_default_risk_control_center_vm() -> RiskControlCenterVM:
    return RiskControlCenterVM(
        overview=[
            RiskMetricVM("Уровень", "Высокий", "HIGH", "План P1", "/risk"),
            RiskMetricVM("Корреляция", "P1", "HIGH", "Проверить", "/risk"),
            RiskMetricVM("Kill Switch", "Готово", "READY", "Детали", "/risk"),
            RiskMetricVM("Micro Live", "Выкл.", "DISABLED", "Детали", "/risk"),
        ],
        rules=[
            RiskRuleVM("Риск на сделку", "н/д", "лимит", "READY", "Контроль"),
            RiskRuleVM("Дневной убыток", "н/д", "лимит", "READY", "Контроль"),
            RiskRuleVM("Экспозиция", "н/д", "лимит", "READY", "Контроль"),
            RiskRuleVM("Корреляция", "Высокая", "P1", "HIGH", "План P1"),
        ],
        events=[
            RiskEventVM("Сейчас", "Корреляционный риск", "P1", "HIGH"),
            RiskEventVM("Сейчас", "Исполнение выключено", "SAFE", "READY"),
            RiskEventVM("Сейчас", "Micro Live выключен", "SAFE", "DISABLED"),
        ],
        actions=[
            RiskMetricVM("План P1", "Открыть", "HIGH", "Открыть", "/risk"),
            RiskMetricVM("Выполн.", "Проверить", "READY", "Открыть", "/execution"),
            RiskMetricVM("Система", "Диагн.", "INFO", "Открыть", "/system"),
        ],
    )
