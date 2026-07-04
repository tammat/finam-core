from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from strategy.base.strategy_result import StrategyResult


class Strategy(ABC):
    name: str
    family: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, feature_snapshot: dict[str, Any]) -> StrategyResult:
        raise NotImplementedError
