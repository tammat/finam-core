from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TradeFill:
    symbol: str
    side: str
    price: float
    qty: float
    commission: float = 0.0


@dataclass(frozen=True)
class ReconstructedClosedTrade:
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    gross_pnl: float
    commission: float
    pnl: float


@dataclass
class OpenLot:
    side: str
    price: float
    qty: float
    commission_left: float


def _normalize_side(side: str) -> str:
    value = str(side).lower().strip()

    if value in {"buy", "b", "bid", "long"}:
        return "buy"

    if value in {"sell", "s", "ask", "short"}:
        return "sell"

    return value


def reconstruct_closed_trades_fifo(
    symbol: str,
    fills: Iterable[TradeFill],
    fallback_commission_rate: float = 0.0,
) -> list[ReconstructedClosedTrade]:
    """
    Восстанавливает закрытые сделки FIFO с учетом комиссии.

    Логика:
    - если комиссия есть в trades, берем ее из fill.commission;
    - если комиссии нет, рассчитываем как price * qty * fallback_commission_rate;
    - комиссия входа распределяется пропорционально закрываемому количеству;
    - комиссия выхода распределяется по закрываемому количеству текущего sell-fill.
    """

    open_lots: list[OpenLot] = []
    closed: list[ReconstructedClosedTrade] = []

    for fill in fills:
        if fill.symbol != symbol:
            continue

        side = _normalize_side(fill.side)
        price = float(fill.price)
        qty_left = float(fill.qty)

        if qty_left <= 0 or price <= 0:
            continue

        fill_commission = float(fill.commission or 0.0)
        if fill_commission == 0.0 and fallback_commission_rate > 0:
            fill_commission = price * qty_left * fallback_commission_rate

        if side == "buy":
            open_lots.append(
                OpenLot(
                    side="buy",
                    price=price,
                    qty=qty_left,
                    commission_left=fill_commission,
                )
            )
            continue

        if side != "sell":
            continue

        sell_qty_total = qty_left
        sell_commission_left = fill_commission

        while qty_left > 0 and open_lots:
            lot = open_lots[0]
            matched_qty = min(lot.qty, qty_left)

            entry_commission = 0.0
            if lot.qty > 0:
                entry_commission = lot.commission_left * (matched_qty / lot.qty)

            exit_commission = 0.0
            if sell_qty_total > 0:
                exit_commission = sell_commission_left * (matched_qty / qty_left)

            gross_pnl = (price - lot.price) * matched_qty
            total_commission = entry_commission + exit_commission
            net_pnl = gross_pnl - total_commission

            closed.append(
                ReconstructedClosedTrade(
                    symbol=symbol,
                    side="long",
                    entry_price=lot.price,
                    exit_price=price,
                    qty=round(matched_qty, 10),
                    gross_pnl=round(gross_pnl, 10),
                    commission=round(total_commission, 10),
                    pnl=round(net_pnl, 10),
                )
            )

            lot.qty -= matched_qty
            lot.commission_left -= entry_commission

            qty_left -= matched_qty
            sell_commission_left -= exit_commission

            if lot.qty <= 0:
                open_lots.pop(0)

    return closed
