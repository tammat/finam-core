from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyWeightInput:
    symbol: str
    strategy: str
    health_score: float
    status: str
    base_qty: float
    regime: str = "UNKNOWN"


@dataclass(frozen=True)
class StrategyWeightDecision:
    symbol: str
    strategy: str
    regime: str
    status: str
    base_qty: float
    size_multiplier: float
    adjusted_qty: float
    allow_trade: bool
    watch_only: bool
    reason: str


class AdaptiveStrategyWeightingEngine:
    """Русский комментарий: переводит здоровье стратегии в размер позиции и режим допуска."""

    def __init__(
        self,
        min_qty: float = 0.0,
        weak_score: float = 30.0,
        strong_score: float = 75.0,
        max_multiplier: float = 1.5,
    ) -> None:
        self.min_qty = float(min_qty)
        self.weak_score = float(weak_score)
        self.strong_score = float(strong_score)
        self.max_multiplier = float(max_multiplier)

    def decide(self, data: StrategyWeightInput) -> StrategyWeightDecision:
        score = max(0.0, min(float(data.health_score), 100.0))
        status = str(data.status or "").upper()
        base_qty = max(0.0, float(data.base_qty or 0.0))

        if status in {"ОТКЛЮЧИТЬ", "НЕДОСТАТОЧНО_ДАННЫХ"}:
            return self._decision(data, base_qty, 0.0, False, True, "Стратегия отключена или данных недостаточно")

        if status == "ТОЛЬКО_НАБЛЮДАТЬ":
            return self._decision(data, base_qty, 0.0, False, True, "Стратегия переведена в режим наблюдения")

        if score < self.weak_score:
            return self._decision(data, base_qty, 0.25, True, False, "Слабый health-score: размер позиции снижен")

        if score >= self.strong_score and status == "УСИЛИТЬ":
            return self._decision(data, base_qty, self.max_multiplier, True, False, "Сильный health-score: размер позиции усилен")

        return self._decision(data, base_qty, 1.0, True, False, "Health-score нейтральный: базовый размер позиции")

    def _decision(
        self,
        data: StrategyWeightInput,
        base_qty: float,
        multiplier: float,
        allow_trade: bool,
        watch_only: bool,
        reason: str,
    ) -> StrategyWeightDecision:
        adjusted_qty = round(base_qty * multiplier, 8)

        if allow_trade and adjusted_qty < self.min_qty:
            allow_trade = False
            watch_only = True
            reason = "Расчётный размер позиции ниже минимального порога"

        return StrategyWeightDecision(
            symbol=data.symbol,
            strategy=data.strategy,
            regime=data.regime,
            status=data.status,
            base_qty=base_qty,
            size_multiplier=float(multiplier),
            adjusted_qty=adjusted_qty,
            allow_trade=allow_trade,
            watch_only=watch_only,
            reason=reason,
        )
