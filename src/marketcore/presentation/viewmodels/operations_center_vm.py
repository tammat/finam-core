from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OperationsMetricVM:
    title: str
    value: str
    status: str
    action_label: str = "Подробнее"
    action_href: str = "#"


@dataclass(frozen=True)
class OperationsServiceVM:
    service: str
    state: str
    uptime: str
    status: str


@dataclass(frozen=True)
class OperationsEventVM:
    time_label: str
    event: str
    level: str
    status: str


@dataclass(frozen=True)
class OperationsCenterVM:
    title: str = "Эксплуатация"
    subtitle: str = "Operations Center"

    overview: list[OperationsMetricVM] = field(default_factory=list)
    services: list[OperationsServiceVM] = field(default_factory=list)
    events: list[OperationsEventVM] = field(default_factory=list)
    actions: list[OperationsMetricVM] = field(default_factory=list)


def build_default_operations_center_vm() -> OperationsCenterVM:
    return OperationsCenterVM(
        overview=[
            OperationsMetricVM("Сервисы", "8", "READY", "Открыть", "/operations"),
            OperationsMetricVM("Ошибки", "0", "READY", "Открыть", "/operations"),
            OperationsMetricVM("Состояние", "Норма", "READY", "Открыть", "/operations"),
            OperationsMetricVM("Журнал", "Готово", "READY", "Открыть", "/operations"),
        ],
        services=[
            OperationsServiceVM("Dashboard", "Работает", "24 ч", "READY"),
            OperationsServiceVM("Paper Runtime", "Работает", "24 ч", "READY"),
            OperationsServiceVM("Research", "Работает", "24 ч", "READY"),
            OperationsServiceVM("Market", "Работает", "24 ч", "READY"),
        ],
        events=[
            OperationsEventVM("Сейчас", "Система запущена", "INFO", "READY"),
            OperationsEventVM("Сейчас", "Ошибок нет", "INFO", "READY"),
            OperationsEventVM("Сейчас", "Все сервисы доступны", "INFO", "READY"),
        ],
        actions=[
            OperationsMetricVM("Диагн.", "Открыть", "INFO", "Открыть", "/system"),
            OperationsMetricVM("Логи", "Открыть", "READY", "Открыть", "/operations"),
            OperationsMetricVM("Dashboard", "Открыть", "READY", "Открыть", "/"),
        ],
    )
