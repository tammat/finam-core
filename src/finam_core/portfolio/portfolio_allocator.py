from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyAllocationInput:
    strategy: str
    symbol: str
    grade: str
    stability_score: float
    p_positive: float
    max_drawdown: float


@dataclass(frozen=True)
class StrategyAllocation:
    strategy: str
    symbol: str
    capital_weight: float
    risk_multiplier: float
    decision: str
    reason: str


class PortfolioAllocator:
    """Русский комментарий: распределяет капитал между стратегиями по качеству и ограничениям риска."""

    GRADE_WEIGHTS = {
        "A+": 1.0,
        "A": 0.7,
        "B": 0.4,
        "C": 0.1,
        "D": 0.0,
        "N": 0.0,
    }

    def allocate(
        self,
        items: list[StrategyAllocationInput],
        *,
        max_strategy_weight: float = 0.35,
        max_symbol_weight: float = 0.40,
    ) -> list[StrategyAllocation]:
        raw = []

        for item in items:
            base_weight = self.GRADE_WEIGHTS.get(item.grade, 0.0)

            if item.max_drawdown < -5.0:
                base_weight *= 0.5

            if item.p_positive < 0.70:
                base_weight = 0.0

            raw.append((item, max(0.0, float(base_weight))))

        total = sum(weight for _, weight in raw)

        if total <= 0:
            return [
                StrategyAllocation(
                    strategy=item.strategy,
                    symbol=item.symbol,
                    capital_weight=0.0,
                    risk_multiplier=0.0,
                    decision="НЕ_РАСПРЕДЕЛЯТЬ",
                    reason="нет_допустимых_стратегий",
                )
                for item, _ in raw
            ]

        normalized = [
            (item, min(weight / total, max_strategy_weight))
            for item, weight in raw
        ]

        symbol_totals: dict[str, float] = {}

        allocations: list[StrategyAllocation] = []

        for item, weight in normalized:
            symbol_used = symbol_totals.get(item.symbol, 0.0)
            available_symbol_weight = max(0.0, max_symbol_weight - symbol_used)
            final_weight = min(weight, available_symbol_weight)
            symbol_totals[item.symbol] = symbol_used + final_weight

            if final_weight <= 0:
                decision = "НЕ_РАСПРЕДЕЛЯТЬ"
                reason = "лимит_по_инструменту"
            else:
                decision = "РАСПРЕДЕЛИТЬ"
                reason = f"grade={item.grade};p_positive={item.p_positive:.4f}"

            allocations.append(
                StrategyAllocation(
                    strategy=item.strategy,
                    symbol=item.symbol,
                    capital_weight=round(final_weight, 6),
                    risk_multiplier=round(final_weight / max_strategy_weight, 6)
                    if max_strategy_weight > 0
                    else 0.0,
                    decision=decision,
                    reason=reason,
                )
            )

        return allocations
