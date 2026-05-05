# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NgSignal:
    symbol: str
    side: str
    qty: float
    price: float
    reason: str
    features: dict


class NgVolatilityBreakout:
    """Русский комментарий: отдельная conservative breakout-стратегия для NG."""

    def __init__(
        self,
        symbol: str = "NGK6@RTSX",
        lookback: int = 20,
        atr_period: int = 14,
        breakout_atr_k: float = 0.35,
        stop_atr_k: float = 2.5,
        take_atr_k: float = 4.0,
        min_atr_pct: float = 0.004,
        max_atr_pct: float = 0.08,
    ) -> None:
        self.symbol = symbol
        self.lookback = lookback
        self.atr_period = atr_period
        self.breakout_atr_k = breakout_atr_k
        self.stop_atr_k = stop_atr_k
        self.take_atr_k = take_atr_k
        self.min_atr_pct = min_atr_pct
        self.max_atr_pct = max_atr_pct
        self._last_key: str | None = None

    def _atr(self, bars: list[dict]) -> float:
        recent = bars[-self.atr_period:]
        ranges = [float(b["high"]) - float(b["low"]) for b in recent]
        return sum(ranges) / max(len(ranges), 1)

    def on_bars(self, bars: list[dict]) -> Optional[NgSignal]:
        if len(bars) < max(self.lookback, self.atr_period) + 1:
            return None

        last = bars[-1]
        prev = bars[-self.lookback - 1:-1]

        price = float(last["close"])
        atr = self._atr(bars)

        if price <= 0 or atr <= 0:
            return None

        atr_pct = atr / price
        if atr_pct < self.min_atr_pct:
            return None
        if atr_pct > self.max_atr_pct:
            return None

        high = max(float(b["high"]) for b in prev)
        low = min(float(b["low"]) for b in prev)

        buy_trigger = high + atr * self.breakout_atr_k
        sell_trigger = low - atr * self.breakout_atr_k

        if price >= buy_trigger:
            key = f"BUY:{round(high, 4)}"
            if key == self._last_key:
                return None
            self._last_key = key

            return NgSignal(
                symbol=self.symbol,
                side="BUY",
                qty=1.0,
                price=price,
                reason="ng_volatility_breakout_buy",
                features={
                    "entry": price,
                    "stop": price - atr * self.stop_atr_k,
                    "take": price + atr * self.take_atr_k,
                    "atr": atr,
                    "atr_pct": atr_pct,
                    "breakout_level": high,
                    "rr": self.take_atr_k / self.stop_atr_k,
                },
            )

        if price <= sell_trigger:
            key = f"SELL:{round(low, 4)}"
            if key == self._last_key:
                return None
            self._last_key = key

            return NgSignal(
                symbol=self.symbol,
                side="SELL",
                qty=1.0,
                price=price,
                reason="ng_volatility_breakout_sell",
                features={
                    "entry": price,
                    "stop": price + atr * self.stop_atr_k,
                    "take": price - atr * self.take_atr_k,
                    "atr": atr,
                    "atr_pct": atr_pct,
                    "breakout_level": low,
                    "rr": self.take_atr_k / self.stop_atr_k,
                },
            )

        return None
