from __future__ import annotations

from marketcore.presentation.viewmodels.operations_center_vm import (
    OperationsCenterVM,
    build_default_operations_center_vm,
)


class OperationsCenterService:
    def load(self) -> OperationsCenterVM:
        return build_default_operations_center_vm()
