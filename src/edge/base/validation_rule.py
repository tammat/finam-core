from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from edge.base.validation_result import EdgeValidationResult

class EdgeValidationRule(ABC):
    name: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, edge_snapshot: dict[str, Any]) -> EdgeValidationResult:
        raise NotImplementedError
