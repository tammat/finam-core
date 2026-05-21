from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class TradeWindow:
    trade_index: int
    symbol: str
    side: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    qty: float
    pnl: float


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    ts: datetime
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class IntrabarQuality:
    trade_index: int
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    mae: float
    mfe: float
    max_favorable_price: float
    max_adverse_price: float
    exit_efficiency: float


def reconstruct_intrabar_quality(
    trades: Iterable[TradeWindow],
    bars: Iterable[MarketBar],
) -> list[IntrabarQuality]:
    """
    Рассчитывает реальный MAE/MFE по барам внутри жизненного цикла сделки.

    Long:
    - MFE = max(high) - entry_price
    - MAE = min(low) - entry_price

    Short:
    - MFE = entry_price - min(low)
    - MAE = entry_price - max(high)

    exit_efficiency:
    - для long: (exit - entry) / MFE
    - для short: (entry - exit) / MFE
    """

    bar_list = list(bars)
    result: list[IntrabarQuality] = []

    for trade in trades:
        trade_bars = [
            bar for bar in bar_list
            if bar.symbol == trade.symbol
            and trade.entry_time <= bar.ts <= trade.exit_time
        ]

        if not trade_bars:
            continue

        side = trade.side.lower().strip()

        max_high = max(float(bar.high) for bar in trade_bars)
        min_low = min(float(bar.low) for bar in trade_bars)

        if side in {"long", "buy"}:
            mfe = max_high - trade.entry_price
            mae = min_low - trade.entry_price
            favorable_price = max_high
            adverse_price = min_low
            raw_exit_move = trade.exit_price - trade.entry_price

        elif side in {"short", "sell"}:
            mfe = trade.entry_price - min_low
            mae = trade.entry_price - max_high
            favorable_price = min_low
            adverse_price = max_high
            raw_exit_move = trade.entry_price - trade.exit_price

        else:
            continue

        exit_efficiency = raw_exit_move / mfe if mfe > 0 else 0.0

        result.append(
            IntrabarQuality(
                trade_index=trade.trade_index,
                symbol=trade.symbol,
                side=side,
                entry_price=round(trade.entry_price, 10),
                exit_price=round(trade.exit_price, 10),
                qty=round(trade.qty, 10),
                pnl=round(trade.pnl, 10),
                mae=round(mae, 10),
                mfe=round(mfe, 10),
                max_favorable_price=round(favorable_price, 10),
                max_adverse_price=round(adverse_price, 10),
                exit_efficiency=round(exit_efficiency, 10),
            )
        )

    return result
