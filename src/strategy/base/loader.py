from __future__ import annotations

from typing import Any

from strategy.base.registry import StrategyRegistry
from strategy.base.strategy_result import StrategyResult


class StrategyLoader:
    def run_all(self, feature_snapshot: dict[str, Any]) -> list[StrategyResult]:
        results: list[StrategyResult] = []
        for strategy_cls in StrategyRegistry.enabled():
            strategy = strategy_cls()
            results.append(strategy.run(feature_snapshot))
        return results
