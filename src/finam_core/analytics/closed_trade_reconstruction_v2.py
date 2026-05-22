from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TradeFillV2:
    trade_id: int
    ts: datetime
    symbol: str
    side: str
    qty: float
    price: float
    strategy: str
    timeframe: str
    trade_source: str
    origin: str
    fill_id: str


@dataclass(frozen=True)
class ClosedTradeChainV2:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    entry_trade_id: int
    exit_trade_id: int
    entry_ts: datetime
    exit_ts: datetime
    side: str
    qty: float
    entry_price: float
    exit_price: float
    pnl: float
    duration_sec: float
    entry_fill_id: str
    exit_fill_id: str
    attribution_status: str


def reconstruct_closed_trades_v2(
    fills: list[TradeFillV2],
) -> list[ClosedTradeChainV2]:
    """
    Русский комментарий:
    FIFO-реконструкция закрытых сделок v2.
    Пока deliberately simple:
    - один символ;
    - одна стратегия;
    - paper/research fills;
    - BUY закрывается SELL, SELL закрывается BUY.
    """

    open_lots: list[TradeFillV2] = []
    closed: list[ClosedTradeChainV2] = []

    ordered = sorted(fills, key=lambda x: (x.ts, x.trade_id))

    for fill in ordered:
        side = fill.side.upper()
        qty_left = abs(float(fill.qty))

        if qty_left <= 0:
            continue

        while qty_left > 1e-12 and open_lots:
            lot = open_lots[0]

            if lot.side.upper() == side:
                break

            close_qty = min(abs(float(lot.qty)), qty_left)

            if lot.side.upper() == "BUY" and side == "SELL":
                pnl = (fill.price - lot.price) * close_qty
                trade_side = "LONG"
            elif lot.side.upper() == "SELL" and side == "BUY":
                pnl = (lot.price - fill.price) * close_qty
                trade_side = "SHORT"
            else:
                break

            closed.append(
                ClosedTradeChainV2(
                    symbol=fill.symbol,
                    strategy=lot.strategy or fill.strategy,
                    timeframe=lot.timeframe or fill.timeframe,
                    trade_source=fill.trade_source,
                    entry_trade_id=lot.trade_id,
                    exit_trade_id=fill.trade_id,
                    entry_ts=lot.ts,
                    exit_ts=fill.ts,
                    side=trade_side,
                    qty=close_qty,
                    entry_price=lot.price,
                    exit_price=fill.price,
                    pnl=pnl,
                    duration_sec=(fill.ts - lot.ts).total_seconds(),
                    entry_fill_id=lot.fill_id,
                    exit_fill_id=fill.fill_id,
                    attribution_status="MATCHED_FIFO",
                )
            )

            lot_remaining = abs(float(lot.qty)) - close_qty
            qty_left -= close_qty

            if lot_remaining <= 1e-12:
                open_lots.pop(0)
            else:
                open_lots[0] = TradeFillV2(
                    trade_id=lot.trade_id,
                    ts=lot.ts,
                    symbol=lot.symbol,
                    side=lot.side,
                    qty=lot_remaining,
                    price=lot.price,
                    strategy=lot.strategy,
                    timeframe=lot.timeframe,
                    trade_source=lot.trade_source,
                    origin=lot.origin,
                    fill_id=lot.fill_id,
                )

        if qty_left > 1e-12:
            open_lots.append(
                TradeFillV2(
                    trade_id=fill.trade_id,
                    ts=fill.ts,
                    symbol=fill.symbol,
                    side=side,
                    qty=qty_left,
                    price=fill.price,
                    strategy=fill.strategy,
                    timeframe=fill.timeframe,
                    trade_source=fill.trade_source,
                    origin=fill.origin,
                    fill_id=fill.fill_id,
                )
            )

    return closed
