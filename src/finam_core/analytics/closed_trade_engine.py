from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Fill:
    """Русский комментарий: нормализованный fill для сборки закрытых сделок."""

    symbol: str
    side: str
    qty: float
    price: float
    commission: float
    strategy: str
    timeframe: str
    ts: datetime


@dataclass(frozen=True)
class ClosedTrade:
    """Русский комментарий: завершенная сделка entry->exit."""

    symbol: str
    strategy: str
    timeframe: str
    side: str
    qty: float
    entry_price: float
    exit_price: float
    gross_pnl: float
    commission: float
    net_pnl: float
    opened_at: datetime
    closed_at: datetime
    holding_seconds: int


def build_closed_trades_fifo(fills: list[Fill]) -> list[ClosedTrade]:
    """
    Русский комментарий:
    Собирает закрытые сделки по FIFO.

    Ограничение v1:
    - поддерживаем простую пару BUY -> SELL;
    - short lifecycle добавим отдельно;
    - partial matching поддержан через остаток qty.
    """
    opened: list[Fill] = []
    closed: list[ClosedTrade] = []

    for fill in sorted(fills, key=lambda x: x.ts):
        side = fill.side.upper()

        if side == "BUY":
            opened.append(fill)
            continue

        if side != "SELL":
            continue

        remaining_sell_qty = fill.qty

        while remaining_sell_qty > 0 and opened:
            entry = opened.pop(0)
            matched_qty = min(entry.qty, remaining_sell_qty)

            gross_pnl = (fill.price - entry.price) * matched_qty
            commission = entry.commission + fill.commission
            net_pnl = gross_pnl - commission

            holding_seconds = int((fill.ts - entry.ts).total_seconds())

            closed.append(
                ClosedTrade(
                    symbol=fill.symbol,
                    strategy=entry.strategy or fill.strategy or "unknown",
                    timeframe=entry.timeframe or fill.timeframe or "unknown",
                    side="LONG",
                    qty=round(matched_qty, 8),
                    entry_price=entry.price,
                    exit_price=fill.price,
                    gross_pnl=round(gross_pnl, 8),
                    commission=round(commission, 8),
                    net_pnl=round(net_pnl, 8),
                    opened_at=entry.ts,
                    closed_at=fill.ts,
                    holding_seconds=max(0, holding_seconds),
                )
            )

            remaining_sell_qty -= matched_qty

            if entry.qty > matched_qty:
                opened.insert(
                    0,
                    Fill(
                        symbol=entry.symbol,
                        side=entry.side,
                        qty=entry.qty - matched_qty,
                        price=entry.price,
                        commission=0.0,
                        strategy=entry.strategy,
                        timeframe=entry.timeframe,
                        ts=entry.ts,
                    ),
                )

    return closed
