# -*- coding: utf-8 -*-
"""
EntryPointSelector — выбор точки входа.

Русский комментарий:
- Strategy даёт направление BUY/SELL.
- EntryPointSelector рассчитывает entry_price, stop_loss, take_profit.
- Заявки не отправляет.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryPoint:
    symbol: str
    side: str
    qty: float
    entry_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str


class EntryPointSelector:
    def __init__(
        self,
        *,
        tick_size: float = 0.01,
        stop_atr_mult: float = 1.5,
        take_atr_mult: float = 2.0,
    ) -> None:
        self.tick_size = float(tick_size)
        self.stop_atr_mult = float(stop_atr_mult)
        self.take_atr_mult = float(take_atr_mult)

    def select(self, intent: dict, market_state: dict) -> EntryPoint | None:
        symbol = str(intent.get("symbol") or "")
        side = str(intent.get("side") or "").upper()
        qty = float(intent.get("qty") or 0.0)

        if not symbol or side not in {"BUY", "SELL"} or qty <= 0:
            return None

        last = float(
            market_state.get("last")
            or market_state.get("price")
            or intent.get("price")
            or 0.0
        )

        atr = float(
            market_state.get("atr")
            or market_state.get("ATR")
            or intent.get("atr")
            or 0.0
        )

        if last <= 0 or atr <= 0:
            return None

        if side == "BUY":
            entry_price = last + self.tick_size
            stop_loss = entry_price - atr * self.stop_atr_mult
            take_profit = entry_price + atr * self.take_atr_mult
        else:
            entry_price = last - self.tick_size
            stop_loss = entry_price + atr * self.stop_atr_mult
            take_profit = entry_price - atr * self.take_atr_mult

        return EntryPoint(
            symbol=symbol,
            side=side,
            qty=qty,
            entry_type="LIMIT",
            entry_price=round(entry_price, 6),
            stop_loss=round(stop_loss, 6),
            take_profit=round(take_profit, 6),
            reason="entry_point_selected_atr_limit",
        )

    def enrich_intent(self, intent: dict, market_state: dict) -> dict | None:
        entry = self.select(intent, market_state)
        if entry is None:
            return intent

        enriched = dict(intent)
        enriched["entry_type"] = entry.entry_type
        enriched["price"] = entry.entry_price
        enriched["entry_price"] = entry.entry_price
        enriched["stop_loss"] = entry.stop_loss
        enriched["take_profit"] = entry.take_profit
        enriched["entry_reason"] = entry.reason
        return enriched
