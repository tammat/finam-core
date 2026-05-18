from __future__ import annotations

from dataclasses import dataclass
import math

from finam_core.research.research_portfolio_equity import EquityPoint


@dataclass(frozen=True)
class ResearchPortfolioMetrics:
    points: int
    net_pnl: float
    max_drawdown: float
    expectancy: float
    volatility: float
    sharpe_like: float
    recovery_factor: float
    winrate: float


class ResearchPortfolioMetricsEngine:
    """Русский комментарий: считает метрики исследовательского портфеля по equity curve."""

    def calculate(self, points: list[EquityPoint]) -> ResearchPortfolioMetrics:
        if not points:
            return ResearchPortfolioMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        pnls = [float(p.weighted_pnl) for p in points]
        net_pnl = float(points[-1].equity)
        max_drawdown = min(float(p.drawdown) for p in points)
        expectancy = sum(pnls) / len(pnls)

        if len(pnls) > 1:
            mean = expectancy
            variance = sum((x - mean) ** 2 for x in pnls) / (len(pnls) - 1)
            volatility = math.sqrt(variance)
        else:
            volatility = 0.0

        sharpe_like = expectancy / volatility if volatility > 0 else 0.0
        recovery_factor = net_pnl / abs(max_drawdown) if max_drawdown < 0 else 0.0
        winrate = sum(1 for x in pnls if x > 0) / len(pnls)

        return ResearchPortfolioMetrics(
            points=len(points),
            net_pnl=round(net_pnl, 6),
            max_drawdown=round(max_drawdown, 6),
            expectancy=round(expectancy, 6),
            volatility=round(volatility, 6),
            sharpe_like=round(sharpe_like, 6),
            recovery_factor=round(recovery_factor, 6),
            winrate=round(winrate, 6),
        )
