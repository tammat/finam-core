from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class TradeGateDecision:
    allowed: bool
    reason: str
    adjusted_qty: float | None = None


class TradeGateService:
    """
    Русский комментарий:
    Единый runtime gate для entry path.

    Этап 1:
    - cooldown;
    - trade limit;
    - без изменения текущей логики pipeline.
    """

    def __init__(
        self,
        base_cooldown_sec: float = 45.0,
        max_trades_per_hour: int = 5,
        max_trades_per_symbol: int = 2,
    ) -> None:
        self.base_cooldown_sec = float(base_cooldown_sec)
        self.max_trades_per_hour = int(max_trades_per_hour)
        self.max_trades_per_symbol = int(max_trades_per_symbol)

        self.last_trade_ts: float = 0.0
        self.trade_timestamps: list[float] = []
        self.symbol_trade_timestamps: dict[str, list[float]] = {}

    def cooldown_allows(self, symbol: str, price: float, atr: float | None = None) -> TradeGateDecision:
        now_ts = time.time()

        try:
            atr_pct = abs(float(atr or 0.0) / float(price)) if price else 0.0

            if atr_pct > 0.015:
                cooldown_sec = self.base_cooldown_sec * 0.6
            elif atr_pct < 0.005:
                cooldown_sec = self.base_cooldown_sec * 1.5
            else:
                cooldown_sec = self.base_cooldown_sec
        except Exception:
            cooldown_sec = self.base_cooldown_sec

        if now_ts - self.last_trade_ts < cooldown_sec:
            return TradeGateDecision(
                allowed=False,
                reason=f"cooldown_block:symbol={symbol}:cooldown={round(cooldown_sec, 3)}",
            )

        return TradeGateDecision(allowed=True, reason="cooldown_ok")

    def trade_limit_allows(self, symbol: str) -> TradeGateDecision:
        now_ts = time.time()

        trades = [t for t in self.trade_timestamps if now_ts - t < 3600]
        if len(trades) >= self.max_trades_per_hour:
            self.trade_timestamps = trades
            return TradeGateDecision(False, "trade_limit_block_global")

        sym_trades = self.symbol_trade_timestamps.get(symbol, [])
        sym_trades = [t for t in sym_trades if now_ts - t < 3600]

        if len(sym_trades) >= self.max_trades_per_symbol:
            self.symbol_trade_timestamps[symbol] = sym_trades
            return TradeGateDecision(False, f"trade_limit_block_symbol:{symbol}")

        return TradeGateDecision(True, "trade_limit_ok")

    def account_trade(self, symbol: str) -> TradeGateDecision:
        now_ts = time.time()

        self.last_trade_ts = now_ts

        trades = [t for t in self.trade_timestamps if now_ts - t < 3600]
        trades.append(now_ts)
        self.trade_timestamps = trades

        sym_trades = self.symbol_trade_timestamps.get(symbol, [])
        sym_trades = [t for t in sym_trades if now_ts - t < 3600]
        sym_trades.append(now_ts)
        self.symbol_trade_timestamps[symbol] = sym_trades

        return TradeGateDecision(
            True,
            f"trade_accounted:global={len(trades)}:symbol={len(sym_trades)}",
        )
