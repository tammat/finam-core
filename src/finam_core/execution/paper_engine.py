from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional


def _get(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass(frozen=True)
class PaperFill:
    symbol: str
    qty: float
    price: float
    commission: float
    fill_id: str


class PaperExecutionEngine:
    """
    Paper execution (default).
    - Accepts intent as dict or object with fields: symbol, side, quantity/qty.
    - Accepts market_state as dict with bid/ask/last/timestamp.
    - Returns PaperFill (filled immediately).
    """

    def __init__(self, slippage_coef: float = 0.25, commission: float = 0.0):
        self.slippage_coef = float(slippage_coef)
        self.commission = float(commission)

    def execute(self, intent: Any, market_state: dict) -> PaperFill:
        symbol = str(_get(intent, "symbol"))
        side = str(_get(intent, "side")).upper()
        qty = _get(intent, "quantity", None)
        if qty is None:
            qty = _get(intent, "qty", None)
        qty = float(qty)

        bid = market_state.get("bid")
        ask = market_state.get("ask")
        last = market_state.get("last")

        # If bid/ask missing (Finam often sends partial quote frames), fallback to last.
        if bid is None and last is not None:
            bid = float(last)
        if ask is None and last is not None:
            ask = float(last)

        if bid is None or ask is None:
            raise ValueError(f"paper_engine: no price in market_state (bid={bid}, ask={ask}, last={last})")

        bid = float(bid)
        ask = float(ask)
        spread = max(ask - bid, 0.0)

        if side == "BUY":
            fill_price = ask + spread * self.slippage_coef
            signed_qty = qty
        elif side == "SELL":
            fill_price = bid - spread * self.slippage_coef
            signed_qty = -qty
        else:
            raise ValueError(f"paper_engine: unknown side={side}")

        ts = market_state.get("timestamp")
        if ts is None:
            ts = time.time()

        return PaperFill(
            symbol=symbol,
            qty=signed_qty,
            price=float(fill_price),
            commission=self.commission,
            fill_id=f"paper_{symbol}_{int(ts*1000)}",
        )
