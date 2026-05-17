from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StrategyScorecardRow:
    strategy: str
    symbol: str
    timeframe: str
    trades: int
    net_pnl: Decimal
    winrate: Decimal
    profit_factor: Decimal
    expectancy: Decimal


@dataclass(frozen=True)
class StrategyRankDecision:
    strategy: str
    symbol: str
    timeframe: str
    decision: str
    score: Decimal
    reason: str


class StrategyRanker:
    """
    Русский комментарий: принимает scorecard стратегии и выдаёт управленческое решение.

    Решения:
    - ENABLE: стратегия пригодна для runtime;
    - REDUCE: стратегия слабая, но не критичная;
    - DISABLE: стратегия статистически непригодна;
    - WATCH: недостаточно сделок для вывода.
    """

    def __init__(
        self,
        *,
        min_trades: int = 30,
        min_expectancy: Decimal = Decimal("0"),
        min_profit_factor: Decimal = Decimal("1.05"),
        min_winrate: Decimal = Decimal("0.45"),
    ) -> None:
        self.min_trades = min_trades
        self.min_expectancy = min_expectancy
        self.min_profit_factor = min_profit_factor
        self.min_winrate = min_winrate

    def rank(self, row: StrategyScorecardRow) -> StrategyRankDecision:
        score = self._score(row)

        if row.trades < self.min_trades:
            return StrategyRankDecision(
                strategy=row.strategy,
                symbol=row.symbol,
                timeframe=row.timeframe,
                decision="WATCH",
                score=score,
                reason=f"not_enough_trades:trades={row.trades}:min={self.min_trades}",
            )

        if row.net_pnl < 0 and row.expectancy < 0:
            return StrategyRankDecision(
                strategy=row.strategy,
                symbol=row.symbol,
                timeframe=row.timeframe,
                decision="DISABLE",
                score=score,
                reason="negative_net_pnl_and_expectancy",
            )

        if row.expectancy <= self.min_expectancy:
            return StrategyRankDecision(
                strategy=row.strategy,
                symbol=row.symbol,
                timeframe=row.timeframe,
                decision="DISABLE",
                score=score,
                reason="expectancy_below_threshold",
            )

        if row.profit_factor < self.min_profit_factor:
            return StrategyRankDecision(
                strategy=row.strategy,
                symbol=row.symbol,
                timeframe=row.timeframe,
                decision="REDUCE",
                score=score,
                reason="profit_factor_below_threshold",
            )

        if row.winrate < self.min_winrate:
            return StrategyRankDecision(
                strategy=row.strategy,
                symbol=row.symbol,
                timeframe=row.timeframe,
                decision="REDUCE",
                score=score,
                reason="winrate_below_threshold",
            )

        return StrategyRankDecision(
            strategy=row.strategy,
            symbol=row.symbol,
            timeframe=row.timeframe,
            decision="ENABLE",
            score=score,
            reason="strategy_passed_scorecard_filters",
        )

    def _score(self, row: StrategyScorecardRow) -> Decimal:
        """
        Русский комментарий: простой устойчивый score v1.

        Не максимизируем PnL напрямую, чтобы не переоценивать одну удачную серию.
        """
        trade_factor = min(Decimal(row.trades) / Decimal("100"), Decimal("1"))
        positive_expectancy = max(row.expectancy, Decimal("0"))
        positive_pnl = max(row.net_pnl, Decimal("0"))

        return (
            positive_expectancy * Decimal("0.50")
            + row.profit_factor * Decimal("0.25")
            + row.winrate * Decimal("0.15")
            + trade_factor * Decimal("0.10")
            + positive_pnl * Decimal("0.001")
        )
