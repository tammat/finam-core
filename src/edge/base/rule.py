from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from edge.base.result import EdgeRuleResult


class EdgeRule(ABC):
    name: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, signal_snapshot: dict[str, Any]) -> EdgeRuleResult:
        raise NotImplementedError
