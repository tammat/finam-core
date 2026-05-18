from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioTrade:
    symbol: str
    exit_ts: str
    net_pnl: float
    weight: float


@dataclass(frozen=True)
class EquityPoint:
    index: int
    ts: str
    symbol: str
    weighted_pnl: float
    equity: float
    drawdown: float


class ResearchPortfolioEquityCurve:
    """Русский комментарий: строит equity curve исследовательского портфеля по закрытым сделкам."""

    def build(self, trades: list[PortfolioTrade]) -> list[EquityPoint]:
        equity = 0.0
        peak = 0.0
        points: list[EquityPoint] = []

        for idx, trade in enumerate(sorted(trades, key=lambda x: x.exit_ts), start=1):
            weighted_pnl = float(trade.net_pnl) * float(trade.weight)
            equity += weighted_pnl
            peak = max(peak, equity)
            drawdown = equity - peak

            points.append(
                EquityPoint(
                    index=idx,
                    ts=trade.exit_ts,
                    symbol=trade.symbol,
                    weighted_pnl=round(weighted_pnl, 6),
                    equity=round(equity, 6),
                    drawdown=round(drawdown, 6),
                )
            )

        return points
