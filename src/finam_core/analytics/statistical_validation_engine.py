from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class StatisticalValidationResult:
    trades: int
    net_pnl: float
    expectancy: float
    winrate: float
    bootstrap_mean_expectancy: float
    expectancy_ci_low: float
    expectancy_ci_high: float
    probability_positive_expectancy: float


class StatisticalValidationEngine:
    """Русский комментарий: статистическая проверка устойчивости результата стратегии."""

    def validate(
        self,
        pnl_values: list[float],
        *,
        bootstrap_samples: int = 1000,
        seed: int = 42,
    ) -> StatisticalValidationResult:
        values = [float(v) for v in pnl_values]

        if not values:
            return StatisticalValidationResult(
                trades=0,
                net_pnl=0.0,
                expectancy=0.0,
                winrate=0.0,
                bootstrap_mean_expectancy=0.0,
                expectancy_ci_low=0.0,
                expectancy_ci_high=0.0,
                probability_positive_expectancy=0.0,
            )

        rng = random.Random(seed)
        n = len(values)

        expectations: list[float] = []

        for _ in range(int(bootstrap_samples)):
            sample = [values[rng.randrange(n)] for _ in range(n)]
            expectations.append(sum(sample) / n)

        expectations.sort()

        low_idx = int(0.025 * (len(expectations) - 1))
        high_idx = int(0.975 * (len(expectations) - 1))

        wins = [v for v in values if v > 0]

        return StatisticalValidationResult(
            trades=n,
            net_pnl=sum(values),
            expectancy=sum(values) / n,
            winrate=len(wins) / n,
            bootstrap_mean_expectancy=sum(expectations) / len(expectations),
            expectancy_ci_low=expectations[low_idx],
            expectancy_ci_high=expectations[high_idx],
            probability_positive_expectancy=sum(1 for x in expectations if x > 0) / len(expectations),
        )
