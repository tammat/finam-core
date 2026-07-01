from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionMetricVM:
    title: str
    value: str
    status: str
    action_label: str = "Подробнее"
    action_href: str = "#"


@dataclass(frozen=True)
class ExecutionOrderVM:
    time_label: str
    symbol: str
    side: str
    qty: str
    status: str


@dataclass(frozen=True)
class ExecutionFillVM:
    time_label: str
    symbol: str
    qty: str
    price: str
    status: str


@dataclass(frozen=True)
class ExecutionCenterVM:
    title: str = "Выполнение"
    subtitle: str = "Execution Center"

    overview: list[ExecutionMetricVM] = field(default_factory=list)
    orders: list[ExecutionOrderVM] = field(default_factory=list)
    fills: list[ExecutionFillVM] = field(default_factory=list)
    actions: list[ExecutionMetricVM] = field(default_factory=list)


def build_default_execution_center_vm() -> ExecutionCenterVM:
    return ExecutionCenterVM(
        overview=[
            ExecutionMetricVM("Исполнение", "Выкл.", "DISABLED", "Детали", "/execution"),
            ExecutionMetricVM("Micro Live", "Выкл.", "DISABLED", "Детали", "/execution"),
            ExecutionMetricVM("Заявки", "0", "READY", "Детали", "/execution"),
            ExecutionMetricVM("Сделки", "0", "READY", "Детали", "/execution"),
        ],
        orders=[
            ExecutionOrderVM("Сейчас", "Нет заявок", "н/д", "0", "READY"),
        ],
        fills=[
            ExecutionFillVM("Сейчас", "Нет сделок", "0", "н/д", "READY"),
        ],
        actions=[
            ExecutionMetricVM("Риски", "Проверить", "HIGH", "Открыть", "/risk"),
            ExecutionMetricVM("Система", "Диагн.", "INFO", "Открыть", "/system"),
            ExecutionMetricVM("Рынок", "Открыть", "READY", "Открыть", "/market"),
        ],
    )
