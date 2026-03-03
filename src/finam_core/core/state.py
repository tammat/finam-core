from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional


def D(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert to Decimal: {x!r}") from e


@dataclass(frozen=True)
class Position:
    symbol: str
    qty: Decimal
    avg_price: Decimal
    unrealized_pnl: Decimal = Decimal("0")

    def __post_init__(self):
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("Position.symbol must be non-empty str")
        if self.avg_price < 0:
            raise ValueError("Position.avg_price must be >= 0")


@dataclass
class PortfolioState:
    cash: Decimal
    positions: Dict[str, Position] = field(default_factory=dict)
    realized_pnl: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    equity: Optional[Decimal] = None  # если задано — сверяем

    def calc_unrealized(self) -> Decimal:
        return sum((p.unrealized_pnl for p in self.positions.values()), Decimal("0"))

    def calc_equity(self) -> Decimal:
        return self.cash + self.calc_unrealized()

    def upsert_position(self, pos: Position) -> None:
        self.positions[pos.symbol] = pos