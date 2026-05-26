from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class FillRow:
    trade_id: int
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0


@dataclass(frozen=True)
class ClosedTrade:
    symbol: str
    entry_trade_id: int
    exit_trade_id: int
    entry_side: str
    exit_side: str
    qty: float
    entry_price: float
    exit_price: float
    gross_pnl: float
    commission: float
    net_pnl: float


def _norm_side(side: str) -> str:
    s = str(side or "").upper()
    if s in {"BUY", "B"}:
        return "BUY"
    if s in {"SELL", "S"}:
        return "SELL"
    return s


def reconstruct_closed_trades(rows: Iterable[dict]) -> List[ClosedTrade]:
    # Простая FIFO-реконструкция закрытых сделок.
    # На этом этапе не меняем БД и не пишем результаты обратно.
    positions: Dict[str, List[FillRow]] = {}
    closed: List[ClosedTrade] = []

    for row in rows:
        fill = FillRow(
            trade_id=int(row["id"]),
            symbol=str(row["symbol"]),
            side=_norm_side(str(row["side"])),
            qty=float(row["qty"]),
            price=float(row["price"]),
            commission=float(row.get("commission") or 0.0),
        )

        book = positions.setdefault(fill.symbol, [])

        remaining_qty = fill.qty

        while remaining_qty > 0 and book and book[0].side != fill.side:
            open_fill = book[0]
            matched_qty = min(open_fill.qty, remaining_qty)

            if open_fill.side == "BUY" and fill.side == "SELL":
                gross_pnl = (fill.price - open_fill.price) * matched_qty
            elif open_fill.side == "SELL" and fill.side == "BUY":
                gross_pnl = (open_fill.price - fill.price) * matched_qty
            else:
                gross_pnl = 0.0

            commission = (
                open_fill.commission * matched_qty / open_fill.qty
                + fill.commission * matched_qty / fill.qty
            )

            closed.append(
                ClosedTrade(
                    symbol=fill.symbol,
                    entry_trade_id=open_fill.trade_id,
                    exit_trade_id=fill.trade_id,
                    entry_side=open_fill.side,
                    exit_side=fill.side,
                    qty=matched_qty,
                    entry_price=open_fill.price,
                    exit_price=fill.price,
                    gross_pnl=gross_pnl,
                    commission=commission,
                    net_pnl=gross_pnl - commission,
                )
            )

            remaining_open_qty = open_fill.qty - matched_qty
            remaining_qty -= matched_qty

            if remaining_open_qty <= 1e-12:
                book.pop(0)
            else:
                book[0] = FillRow(
                    trade_id=open_fill.trade_id,
                    symbol=open_fill.symbol,
                    side=open_fill.side,
                    qty=remaining_open_qty,
                    price=open_fill.price,
                    commission=open_fill.commission,
                )

        if remaining_qty > 1e-12:
            book.append(
                FillRow(
                    trade_id=fill.trade_id,
                    symbol=fill.symbol,
                    side=fill.side,
                    qty=remaining_qty,
                    price=fill.price,
                    commission=fill.commission,
                )
            )

    return closed
