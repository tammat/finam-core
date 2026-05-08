# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PaperSignalTrade:
    symbol: str
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    qty: float
    opened_at: str
    status: str = "OPEN"
    exit_price: float | None = None
    closed_at: str | None = None
    close_reason: str | None = None
    pnl: float = 0.0
    r_multiple: float = 0.0


class SignalPaperTradeTracker:
    def __init__(self) -> None:
        self.trades: list[PaperSignalTrade] = []

    def open_trade(self, *, symbol: str, side: str, entry: float, stop_loss: float, take_profit: float, qty: float = 1.0) -> PaperSignalTrade:
        trade = PaperSignalTrade(
            symbol=str(symbol),
            side=str(side).upper(),
            entry=float(entry),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            qty=float(qty),
            opened_at=datetime.utcnow().isoformat(),
        )
        self.trades.append(trade)
        return trade

    def on_price(self, symbol: str, price: float) -> list[PaperSignalTrade]:
        closed = []
        price = float(price)

        for trade in self.trades:
            if trade.symbol != symbol or trade.status != "OPEN":
                continue

            if trade.side == "BUY":
                if price <= trade.stop_loss:
                    self._close(trade, trade.stop_loss, "STOP_LOSS")
                    closed.append(trade)
                elif price >= trade.take_profit:
                    self._close(trade, trade.take_profit, "TAKE_PROFIT")
                    closed.append(trade)

            elif trade.side == "SELL":
                if price >= trade.stop_loss:
                    self._close(trade, trade.stop_loss, "STOP_LOSS")
                    closed.append(trade)
                elif price <= trade.take_profit:
                    self._close(trade, trade.take_profit, "TAKE_PROFIT")
                    closed.append(trade)

        return closed

    def _close(self, trade: PaperSignalTrade, exit_price: float, reason: str) -> None:
        trade.status = "CLOSED"
        trade.exit_price = float(exit_price)
        trade.closed_at = datetime.utcnow().isoformat()
        trade.close_reason = reason

        if trade.side == "BUY":
            trade.pnl = (trade.exit_price - trade.entry) * trade.qty
            risk = abs(trade.entry - trade.stop_loss) * trade.qty
        else:
            trade.pnl = (trade.entry - trade.exit_price) * trade.qty
            risk = abs(trade.stop_loss - trade.entry) * trade.qty

        trade.r_multiple = round(trade.pnl / risk, 4) if risk > 0 else 0.0
        trade.pnl = round(trade.pnl, 4)

    def daily_summary(self) -> dict:
        closed = [t for t in self.trades if t.status == "CLOSED"]
        open_trades = [t for t in self.trades if t.status == "OPEN"]
        pnl = round(sum(t.pnl for t in closed), 4)
        wins = len([t for t in closed if t.pnl > 0])
        losses = len([t for t in closed if t.pnl < 0])

        return {
            "total": len(self.trades),
            "closed": len(closed),
            "open": len(open_trades),
            "wins": wins,
            "losses": losses,
            "pnl": pnl,
            "avg_r": round(sum(t.r_multiple for t in closed) / len(closed), 4) if closed else 0.0,
            "trades": [asdict(t) for t in self.trades],
        }
