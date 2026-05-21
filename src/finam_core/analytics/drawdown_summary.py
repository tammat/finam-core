from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DrawdownSummary:
    trades: int
    final_pnl: float
    max_drawdown: float
    max_drawdown_trade_index: int
    max_win_streak: int
    max_loss_streak: int
    avg_win: float
    avg_loss: float
    payoff_ratio: float


def build_drawdown_summary(pnls: Iterable[float]) -> DrawdownSummary:
    values = [float(x) for x in pnls]

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    max_drawdown_trade_index = 0

    win_streak = 0
    loss_streak = 0
    max_win_streak = 0
    max_loss_streak = 0

    wins: list[float] = []
    losses: list[float] = []

    for index, pnl in enumerate(values, start=1):
        cumulative += pnl
        peak = max(peak, cumulative)
        drawdown = cumulative - peak

        if drawdown < max_drawdown:
            max_drawdown = drawdown
            max_drawdown_trade_index = index

        if pnl > 0:
            wins.append(pnl)
            win_streak += 1
            loss_streak = 0
        elif pnl < 0:
            losses.append(pnl)
            loss_streak += 1
            win_streak = 0
        else:
            win_streak = 0
            loss_streak = 0

        max_win_streak = max(max_win_streak, win_streak)
        max_loss_streak = max(max_loss_streak, loss_streak)

    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

    return DrawdownSummary(
        trades=len(values),
        final_pnl=round(cumulative, 10),
        max_drawdown=round(max_drawdown, 10),
        max_drawdown_trade_index=max_drawdown_trade_index,
        max_win_streak=max_win_streak,
        max_loss_streak=max_loss_streak,
        avg_win=round(avg_win, 10),
        avg_loss=round(avg_loss, 10),
        payoff_ratio=round(payoff_ratio, 10),
    )
