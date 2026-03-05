from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


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
    """Paper execution (default).

    Design goals for Finam_Core:
    - be permissive to calling code (tests / pipeline) and accept extra kwargs
    - never crash on partial quotes (Finam часто шлёт фреймы без bid/ask/last)
    - produce deterministic fills for simulation (fallback price=0.0 if unknown)

    Expected inputs:
    - intent: dict/object with fields: symbol, side, qty|quantity, price(optional)
    - market_state: dict with bid/ask/last/price/timestamp(optional)
    """

    def __init__(self, slippage_coef: float = 0.25, commission: float = 0.0, **_ignored):
        self.slippage_coef = float(slippage_coef)
        self.commission = float(commission)

    def execute(self, intent: Any, market_state: dict | None = None) -> PaperFill:
        market_state = market_state or {}

        symbol = str(_get(intent, "symbol", "") or "")
        side = str(_get(intent, "side", "BUY") or "BUY").upper()

        qty = _get(intent, "quantity", None)
        if qty is None:
            qty = _get(intent, "qty", 0.0)
        qty = float(qty or 0.0)

        # ---- price extraction (best-effort) ----
        bid = market_state.get("bid", None)
        ask = market_state.get("ask", None)
        last = market_state.get("last", None)
        px = market_state.get("price", None)
        if px is None:
            px = _get(intent, "price", None)

        # Normalize candidates to float when possible
        def _to_float(x):
            try:
                return float(x)
            except Exception:
                return None

        bid_f = _to_float(bid)
        ask_f = _to_float(ask)
        last_f = _to_float(last)
        px_f = _to_float(px)

        # If bid/ask missing (partial quote frames), fall back in this order:
        # last -> px -> 0.0
        fallback = last_f if last_f is not None else (px_f if px_f is not None else 0.0)
        if bid_f is None:
            bid_f = fallback
        if ask_f is None:
            ask_f = fallback

        spread = max((ask_f - bid_f), 0.0)

        if side == "BUY":
            fill_price = ask_f + spread * self.slippage_coef
            signed_qty = qty
        elif side == "SELL":
            fill_price = bid_f - spread * self.slippage_coef
            signed_qty = -qty
        else:
            raise ValueError(f"paper_engine: unknown side={side!r}")

        ts = market_state.get("timestamp")
        if ts is None:
            ts = time.time()
        ts = float(ts) if not isinstance(ts, (int, float)) else ts

        return PaperFill(
            symbol=symbol,
            qty=float(signed_qty),
            price=float(fill_price),
            commission=float(self.commission),
            fill_id=f"paper_{symbol}_{int(ts * 1000)}",
        )
