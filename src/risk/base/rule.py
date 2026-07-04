from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from risk.base.result import RiskRuleResult


class RiskRule(ABC):
    name: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, edge_decision: dict[str, Any]) -> RiskRuleResult:
        raise NotImplementedError
