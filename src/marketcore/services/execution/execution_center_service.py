from __future__ import annotations

from marketcore.presentation.viewmodels.execution_center_vm import (
    ExecutionCenterVM,
    build_default_execution_center_vm,
)


class ExecutionCenterService:
    def load(self) -> ExecutionCenterVM:
        return build_default_execution_center_vm()
