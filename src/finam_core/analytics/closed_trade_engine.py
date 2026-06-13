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

    Поддерживает оба жизненных цикла:
    - BUY -> SELL = LONG;
    - SELL -> BUY = SHORT.
    """
    opened: list[Fill] = []
    closed: list[ClosedTrade] = []

    def position_side(entry_side: str) -> str:
        if entry_side.upper() == "BUY":
            return "LONG"
        if entry_side.upper() == "SELL":
            return "SHORT"
        raise ValueError(f"unknown entry side: {entry_side}")

    def is_opposite(entry_side: str, exit_side: str) -> bool:
        return (
            entry_side.upper() == "BUY" and exit_side.upper() == "SELL"
        ) or (
            entry_side.upper() == "SELL" and exit_side.upper() == "BUY"
        )

    def pnl(pos_side: str, entry_price: float, exit_price: float, qty: float) -> float:
        if pos_side == "LONG":
            return (exit_price - entry_price) * qty
        if pos_side == "SHORT":
            return (entry_price - exit_price) * qty
        raise ValueError(f"unknown position side: {pos_side}")

    for fill in sorted(fills, key=lambda x: x.ts):
        side = fill.side.upper()

        if side not in {"BUY", "SELL"}:
            continue

        remaining_qty = fill.qty

        while remaining_qty > 0 and opened and is_opposite(opened[0].side, side):
            entry = opened.pop(0)
            matched_qty = min(entry.qty, remaining_qty)
            pos_side = position_side(entry.side)

            gross_pnl = pnl(pos_side, entry.price, fill.price, matched_qty)
            commission = entry.commission + fill.commission
            net_pnl = gross_pnl - commission
            holding_seconds = int((fill.ts - entry.ts).total_seconds())

            closed.append(
                ClosedTrade(
                    symbol=fill.symbol,
                    strategy=entry.strategy or fill.strategy or "unknown",
                    timeframe=entry.timeframe or fill.timeframe or "unknown",
                    side=pos_side,
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

            remaining_qty -= matched_qty

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

        if remaining_qty > 0:
            opened.append(
                Fill(
                    symbol=fill.symbol,
                    side=fill.side,
                    qty=remaining_qty,
                    price=fill.price,
                    commission=fill.commission,
                    strategy=fill.strategy,
                    timeframe=fill.timeframe,
                    ts=fill.ts,
                )
            )

    return closed

