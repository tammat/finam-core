from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class StrategyMetrics:
    """Итоговые метрики стратегии по инструменту или режиму рынка."""

    trades: int
    wins: int
    losses: int
    total_pnl: float
    avg_pnl: float
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float


def calculate_strategy_metrics(pnls: Iterable[float]) -> StrategyMetrics:
    """Рассчитывает базовые метрики стратегии по списку PnL сделок."""
    values = [float(x) for x in pnls]
    trades = len(values)

    if trades == 0:
        return StrategyMetrics(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    wins_list = [x for x in values if x > 0]
    losses_list = [x for x in values if x < 0]

    wins = len(wins_list)
    losses = len(losses_list)

    gross_profit = sum(wins_list)
    gross_loss = abs(sum(losses_list))

    total_pnl = sum(values)
    avg_pnl = total_pnl / trades
    win_rate = wins / trades
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for pnl in values:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)

    return StrategyMetrics(
        trades=trades,
        wins=wins,
        losses=losses,
        total_pnl=round(total_pnl, 6),
        avg_pnl=round(avg_pnl, 6),
        win_rate=round(win_rate, 6),
        profit_factor=round(profit_factor, 6),
        expectancy=round(avg_pnl, 6),
        max_drawdown=round(max_drawdown, 6),
    )
