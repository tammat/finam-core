from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass
class BacktestStats:
    total_return: float
    max_drawdown: float
    sharpe: float
    volatility: float


class TradeStats:

    @staticmethod
    def from_equity_curve(equity_curve: List[Tuple]) -> BacktestStats:

        if len(equity_curve) < 2:
            raise ValueError("Not enough data")

        equity = np.array([e[1] for e in equity_curve])

        returns = np.diff(equity) / equity[:-1]

        total_return = equity[-1] / equity[0] - 1

        cumulative_max = np.maximum.accumulate(equity)
        drawdowns = (equity - cumulative_max) / cumulative_max
        max_drawdown = drawdowns.min()

        volatility = np.std(returns) * np.sqrt(252)

        sharpe = (
            np.mean(returns) / np.std(returns) * np.sqrt(252)
            if np.std(returns) > 0 else 0.0
        )

        return BacktestStats(
            total_return=float(total_return),
            max_drawdown=float(max_drawdown),
            sharpe=float(sharpe),
            volatility=float(volatility),
        )