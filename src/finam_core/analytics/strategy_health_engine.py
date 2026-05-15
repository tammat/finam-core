from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyHealthInput:
    symbol: str
    strategy: str
    trades: int
    net_pnl: float
    expectancy: float
    winrate_pct: float
    profit_factor: float | None = None
    max_drawdown: float | None = None


@dataclass(frozen=True)
class StrategyHealthDecision:
    symbol: str
    strategy: str
    status: str
    allow_trade: bool
    watch_only: bool
    risk_multiplier: float
    score: float
    reason: str


class StrategyHealthEngine:
    """Русский комментарий: оценивает здоровье стратегии по чистой attributed-статистике."""

    def __init__(
        self,
        min_trades: int = 3,
        min_winrate_pct: float = 55.0,
        min_expectancy: float = 0.0,
        disable_expectancy: float = 0.0,
    ) -> None:
        self.min_trades = int(min_trades)
        self.min_winrate_pct = float(min_winrate_pct)
        self.min_expectancy = float(min_expectancy)
        self.disable_expectancy = float(disable_expectancy)

    def evaluate(self, data: StrategyHealthInput) -> StrategyHealthDecision:
        if data.trades < self.min_trades:
            return StrategyHealthDecision(
                symbol=data.symbol,
                strategy=data.strategy,
                status="НЕДОСТАТОЧНО_ДАННЫХ",
                allow_trade=False,
                watch_only=True,
                risk_multiplier=0.0,
                score=0.0,
                reason="Недостаточно чистых attributed-сделок для решения",
            )

        score = self._score(data)

        if data.net_pnl > 0 and data.expectancy > self.min_expectancy and data.winrate_pct >= self.min_winrate_pct:
            return StrategyHealthDecision(
                symbol=data.symbol,
                strategy=data.strategy,
                status="УСИЛИТЬ",
                allow_trade=True,
                watch_only=False,
                risk_multiplier=1.2,
                score=score,
                reason="Положительное матожидание, прибыль и достаточная доля прибыльных сделок",
            )

        if data.net_pnl < 0 and data.expectancy < self.disable_expectancy:
            return StrategyHealthDecision(
                symbol=data.symbol,
                strategy=data.strategy,
                status="ОТКЛЮЧИТЬ",
                allow_trade=False,
                watch_only=True,
                risk_multiplier=0.0,
                score=score,
                reason="Отрицательное матожидание и совокупный убыток",
            )

        return StrategyHealthDecision(
            symbol=data.symbol,
            strategy=data.strategy,
            status="ТОЛЬКО_НАБЛЮДАТЬ",
            allow_trade=False,
            watch_only=True,
            risk_multiplier=0.0,
            score=score,
            reason="Торговое преимущество не подтверждено",
        )

    def _score(self, data: StrategyHealthInput) -> float:
        expectancy_score = max(min(data.expectancy, 10.0), -10.0) * 5.0
        winrate_score = (data.winrate_pct - 50.0) * 1.0
        pnl_score = max(min(data.net_pnl, 100.0), -100.0) * 0.1

        pf = data.profit_factor
        profit_factor_score = 0.0
        if pf is not None:
            profit_factor_score = max(min(float(pf), 5.0), 0.0) * 5.0

        score = 50.0 + expectancy_score + winrate_score + pnl_score + profit_factor_score
        return round(max(0.0, min(score, 100.0)), 2)
