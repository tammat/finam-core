from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from finam_core.accounting.position_manager import PositionManager


class PortfolioManager:
    """
    Thin wrapper around PositionManager + cash/equity metrics.

    Expected by risk layer:
      - starting_cash / starting_capital
      - equity() or equity attribute
      - total_exposure, current_symbol_exposure (computed in build_risk_context)
    """

    def __init__(
        self,
        initial_cash: float | None = None,
        *,
        starting_cash: float | None = None,
        position_manager: PositionManager | None = None,
        validator=None,
        price_provider=None,
    ):
        if starting_cash is None:
            starting_cash = initial_cash
        self.starting_cash: float = float(starting_cash or 0.0)
        self.cash: float = float(starting_cash or 0.0)

        self.position_manager: PositionManager = position_manager or PositionManager()

        self._validator = validator
        self._price_provider = price_provider

        self.daily_pnl: float = 0.0  # optional
        self.realized_pnl: float = 0.0

    # --- pricing ---
    def on_price(self, symbol: str, price: float) -> None:
        self.position_manager.on_price(symbol, float(price))

    def update_market_price(self, symbol: str, price: float) -> None:
        self.on_price(symbol, price)

    # --- fills ---
    def on_fill(self, fill) -> float:
        """
        Accepts fill object with .symbol .qty .price or dict-like.
        qty sign convention: +qty for BUY, -qty for SELL.
        Returns realized pnl delta.
        """
        symbol = getattr(fill, "symbol", None) or fill["symbol"]
        qty = float(getattr(fill, "qty", None) if hasattr(fill, "qty") else fill.get("qty"))
        price = float(getattr(fill, "price", None) if hasattr(fill, "price") else fill.get("price"))

        side = "BUY" if qty > 0 else "SELL"
        abs_qty = abs(qty)

        realized = self.position_manager.apply_fill(symbol, side, abs_qty, price)
        self.realized_pnl += float(realized)

        # cash accounting (simplified, no margin): BUY decreases cash, SELL increases cash
        if side == "BUY":
            self.cash -= abs_qty * price
        else:
            self.cash += abs_qty * price

        return float(realized)

    def apply_fill(self, *args, **kwargs):
        """
        Back-compat: proxy to on_fill.
        - apply_fill(fill)
        - apply_fill(symbol=..., side=..., qty=..., price=...)
        """
        if args and len(args) == 1 and not kwargs:
            return self.on_fill(args[0])
        symbol = kwargs.get("symbol") or (args[0] if len(args) > 0 else None)
        side = kwargs.get("side") or (args[1] if len(args) > 1 else None)
        qty = kwargs.get("qty") or (args[2] if len(args) > 2 else None)
        price = kwargs.get("price") or (args[3] if len(args) > 3 else None)
        sign_qty = float(qty) * (1.0 if str(side).upper() == "BUY" else -1.0)
        return self.on_fill({"symbol": symbol, "qty": sign_qty, "price": float(price)})

    # --- metrics ---
    def get_position_qty(self, symbol: str) -> float:
        return self.position_manager.get_position_qty(symbol)

    def equity(self) -> float:
        # cash + sum(qty * mark_price) (mark_price falls back to avg_price)
        eq = float(self.cash)
        for pos in self.position_manager.positions.values():
            px = pos.mark_price if pos.mark_price else pos.avg_price
            eq += pos.qty * px
        return eq

    @property
    def total_equity(self) -> float:
        return self.equity()

    @property
    def total_exposure(self) -> float:
        # gross exposure
        total = 0.0
        for pos in self.position_manager.positions.values():
            px = pos.mark_price if pos.mark_price else pos.avg_price
            total += abs(pos.qty) * px
        return total
