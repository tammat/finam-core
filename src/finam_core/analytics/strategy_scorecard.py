from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class TradeResult:
    symbol: str
    strategy: str
    timeframe: str
    pnl: Decimal
    commission: Decimal = Decimal("0")
    r_multiple: Decimal = Decimal("0")


@dataclass(frozen=True)
class StrategyScorecard:
    symbol: str
    strategy: str
    timeframe: str
    trades: int
    gross_pnl: Decimal
    net_pnl: Decimal
    winrate: Decimal
    profit_factor: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    expectancy: Decimal
    max_drawdown: Decimal
    avg_r: Decimal
    commission_total: Decimal


class StrategyScorecardCalculator:
    """Русский комментарий: считает базовую статистику стратегии по закрытым сделкам."""

    def calculate(self, trades: Iterable[TradeResult]) -> StrategyScorecard:
        rows = list(trades)

        if not rows:
            return StrategyScorecard(
                symbol="unknown",
                strategy="unknown",
                timeframe="unknown",
                trades=0,
                gross_pnl=Decimal("0"),
                net_pnl=Decimal("0"),
                winrate=Decimal("0"),
                profit_factor=Decimal("0"),
                avg_win=Decimal("0"),
                avg_loss=Decimal("0"),
                expectancy=Decimal("0"),
                max_drawdown=Decimal("0"),
                avg_r=Decimal("0"),
                commission_total=Decimal("0"),
            )

        symbol = rows[0].symbol
        strategy = rows[0].strategy
        timeframe = rows[0].timeframe

        gross_pnl = sum((r.pnl for r in rows), Decimal("0"))
        commission_total = sum((r.commission for r in rows), Decimal("0"))
        net_values = [r.pnl - r.commission for r in rows]
        net_pnl = sum(net_values, Decimal("0"))

        wins = [v for v in net_values if v > 0]
        losses = [v for v in net_values if v < 0]

        trades_count = len(rows)
        winrate = Decimal(len(wins)) / Decimal(trades_count)

        gross_profit = sum(wins, Decimal("0"))
        gross_loss_abs = abs(sum(losses, Decimal("0")))

        profit_factor = (
            gross_profit / gross_loss_abs
            if gross_loss_abs != 0
            else Decimal("0")
        )

        avg_win = gross_profit / Decimal(len(wins)) if wins else Decimal("0")
        avg_loss = sum(losses, Decimal("0")) / Decimal(len(losses)) if losses else Decimal("0")
        expectancy = net_pnl / Decimal(trades_count)

        equity = Decimal("0")
        peak = Decimal("0")
        max_drawdown = Decimal("0")

        for value in net_values:
            equity += value
            peak = max(peak, equity)
            drawdown = equity - peak
            max_drawdown = min(max_drawdown, drawdown)

        avg_r = sum((r.r_multiple for r in rows), Decimal("0")) / Decimal(trades_count)

        return StrategyScorecard(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            trades=trades_count,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            winrate=winrate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            max_drawdown=max_drawdown,
            avg_r=avg_r,
            commission_total=commission_total,
        )
