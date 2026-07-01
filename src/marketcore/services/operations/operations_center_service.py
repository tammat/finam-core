from __future__ import annotations

import subprocess

from marketcore.presentation.viewmodels.operations_center_vm import (
    OperationsCenterVM,
    OperationsEventVM,
    OperationsMetricVM,
    OperationsServiceVM,
    build_default_operations_center_vm,
)
from marketcore.services.common.safe_query import safe_query


SERVICES = [
    "finam-marketcore-dashboard.service",
    "finam-paper-runtime.service",
    "finam-research-runtime.service",
    "finam-market-bars-ingestion.service",
]


def _service_state(name: str) -> OperationsServiceVM:
    result = subprocess.run(
        ["systemctl", "is-active", name],
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
    )
    state = result.stdout.strip() or "unknown"

    if state == "active":
        return OperationsServiceVM(name.replace("finam-", "").replace(".service", ""), "Работает", "н/д", "READY")

    return OperationsServiceVM(name.replace("finam-", "").replace(".service", ""), "Проверить", "н/д", "WARNING")


class OperationsCenterService:
    def load(self) -> OperationsCenterVM:
        return safe_query(self._load_from_system, build_default_operations_center_vm())

    def _load_from_system(self) -> OperationsCenterVM:
        services = [_service_state(name) for name in SERVICES]
        errors = sum(1 for s in services if s.status != "READY")

        return OperationsCenterVM(
            title="Эксплуатация",
            subtitle="Operations Center",
            overview=[
                OperationsMetricVM("Сервисы", str(len(services)), "READY", "Открыть", "/operations"),
                OperationsMetricVM("Ошибки", str(errors), "READY" if errors == 0 else "WARNING", "Открыть", "/operations"),
                OperationsMetricVM("Состояние", "Норма" if errors == 0 else "Проверить", "READY" if errors == 0 else "WARNING", "Открыть", "/operations"),
                OperationsMetricVM("Журнал", "Готово", "READY", "Открыть", "/operations"),
            ],
            services=services,
            events=[
                OperationsEventVM("Сейчас", "Состояние сервисов обновлено", "Инфо", "READY"),
                OperationsEventVM("Сейчас", "Ошибок нет" if errors == 0 else "Есть предупреждения", "Инфо", "READY" if errors == 0 else "WARNING"),
                OperationsEventVM("Сейчас", "Исполнение не изменялось", "Безопасно", "READY"),
            ],
            actions=build_default_operations_center_vm().actions,
        )
