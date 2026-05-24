
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)

class StrategyPerformanceSnapshot:

    strategy: str

    symbol: str

    timeframe: str

    regime: str

    trade_source: str

    trades: int

    wins: int

    losses: int

    gross_pnl: float

    net_pnl: float

    gross_profit: float

    gross_loss: float

    profit_factor: float

    winrate: float

    expectancy: float

    avg_rr: float

    max_drawdown: float

    sharpe_like: float

    avg_hold_sec: float

    context_quality: str

    status: str

    reason: str

