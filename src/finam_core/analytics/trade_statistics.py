from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable


@dataclass(frozen=True)
class ClosedTrade:
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float


@dataclass(frozen=True)
class TradeStatistics:
    symbol: str
    trades: int
    wins: int
    losses: int
    winrate: float
    gross_profit: float
    gross_loss: float
    net_pnl: float
    avg_pnl: float
    profit_factor: float
    max_drawdown: float
    expectancy: float
    sharpe_like: float


def calculate_trade_statistics(symbol: str, trades: Iterable[ClosedTrade]) -> TradeStatistics:
    items = [t for t in trades if t.symbol == symbol]

    if not items:
        return TradeStatistics(
            symbol=symbol,
            trades=0,
            wins=0,
            losses=0,
            winrate=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            net_pnl=0.0,
            avg_pnl=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            expectancy=0.0,
            sharpe_like=0.0,
        )

    pnls = [float(t.pnl) for t in items]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_pnl = sum(pnls)
    trades_count = len(items)

    winrate = len(wins) / trades_count
    avg_pnl = net_pnl / trades_count
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        drawdown = equity - peak
        max_drawdown = min(max_drawdown, drawdown)

    mean = avg_pnl
    variance = sum((p - mean) ** 2 for p in pnls) / trades_count
    stdev = sqrt(variance)
    sharpe_like = mean / stdev if stdev > 0 else 0.0

    return TradeStatistics(
        symbol=symbol,
        trades=trades_count,
        wins=len(wins),
        losses=len(losses),
        winrate=round(winrate, 4),
        gross_profit=round(gross_profit, 4),
        gross_loss=round(gross_loss, 4),
        net_pnl=round(net_pnl, 4),
        avg_pnl=round(avg_pnl, 4),
        profit_factor=round(profit_factor, 4),
        max_drawdown=round(max_drawdown, 4),
        expectancy=round(avg_pnl, 4),
        sharpe_like=round(sharpe_like, 4),
    )
