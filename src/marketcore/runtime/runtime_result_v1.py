from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeExecutionStatusV1(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class RuntimeExecutionResultV1:
    """Результат исполнения RenderTree через PlatformDriverV1."""

    status: RuntimeExecutionStatusV1
    nodes_processed: int
    diagnostics: tuple[str, ...] = ()

    @property
    def success(self) -> bool:
        return self.status is RuntimeExecutionStatusV1.SUCCESS
