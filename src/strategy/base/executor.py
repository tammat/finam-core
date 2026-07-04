from __future__ import annotations

from strategy.base.strategy import Strategy
from strategy.base.strategy_result import StrategyResult


class StrategyExecutor:
    def execute(self, strategy: Strategy, feature_snapshot: dict) -> StrategyResult:
        return strategy.run(feature_snapshot)
