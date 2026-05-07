# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionDecision:
    """Русский комментарий: решение о типе исполнения, но не сама заявка."""

    action: str
    symbol: str
    side: str
    qty: float
    order_type: str
    reason: str
    price: float | None = None
    stop_price: float | None = None
    limit_price: float | None = None
    confidence: float = 0.0


class ExecutionDecisionLayer:
    """
    Русский комментарий:
    Выбирает MARKET / STOP / LIMIT / SKIP.
    Заявки брокеру не отправляет.
    """

    VALID_SIDES = {"BUY", "SELL"}

    def decide(self, intent: dict[str, Any], market_state: dict[str, Any] | None = None) -> ExecutionDecision:
        market_state = market_state or {}

        symbol = str(intent.get("symbol") or market_state.get("symbol") or "")
        side = str(intent.get("side") or "").upper()
        qty = float(intent.get("qty") or 0.0)
        price = self._num(intent.get("price"), self._num(market_state.get("last"), 0.0))
        signal_type = str(intent.get("signal_type") or intent.get("reason") or "").lower()
        intent_type = str(intent.get("intent_type") or "").upper()

        if not symbol or side not in self.VALID_SIDES or qty <= 0:
            return self._skip(symbol, side, qty, price, "invalid_intent")

        spread_pct = self._spread_pct(market_state)
        max_spread_pct = self._num(intent.get("max_spread_pct"), 0.0015)
        if spread_pct is not None and spread_pct > max_spread_pct:
            return self._skip(symbol, side, qty, price, f"spread_too_wide:{spread_pct:.6f}>{max_spread_pct:.6f}")

        if intent_type == "EXIT" or bool(intent.get("emergency_exit")):
            return ExecutionDecision(
                action="MARKET",
                symbol=symbol,
                side=side,
                qty=qty,
                order_type="MARKET",
                reason="exit_or_emergency_market",
                price=price,
                confidence=1.0,
            )

        atr = self._num(intent.get("atr"), self._num(market_state.get("atr"), 0.0))
        volume_ratio = self._num(intent.get("volume_ratio"), self._num(market_state.get("volume_ratio"), 1.0))
        range_atr = self._num(intent.get("range_atr"), self._num(market_state.get("range_atr"), 0.0))
        breakout_level = self._num(intent.get("breakout_level"), 0.0)
        regime = str(intent.get("regime") or market_state.get("regime") or "unknown").lower()

        strong_impulse = (
            atr > 0
            and range_atr >= self._num(intent.get("market_range_atr_min"), 2.0)
            and volume_ratio >= self._num(intent.get("market_volume_ratio_min"), 1.5)
            and regime not in {"flat", "unknown", "low_vol"}
        )

        if strong_impulse and bool(intent.get("allow_market_on_impulse")):
            return ExecutionDecision(
                action="MARKET",
                symbol=symbol,
                side=side,
                qty=qty,
                order_type="MARKET",
                reason="confirmed_impulse_market",
                price=price,
                confidence=0.85,
            )

        if breakout_level > 0 or "breakout" in signal_type or "проб" in signal_type:
            stop_price = breakout_level if breakout_level > 0 else price
            return ExecutionDecision(
                action="STOP",
                symbol=symbol,
                side=side,
                qty=qty,
                order_type="STOP",
                reason="breakout_stop_entry",
                price=price,
                stop_price=stop_price,
                confidence=0.75,
            )

        entry_type = str(intent.get("entry_type") or "").upper()
        entry_price = self._num(intent.get("entry_price"), 0.0)
        limit_price = self._num(intent.get("limit_price"), entry_price)

        if entry_type == "LIMIT":
            lp = limit_price if limit_price > 0 else price
            return ExecutionDecision(
                action="LIMIT",
                symbol=symbol,
                side=side,
                qty=qty,
                order_type="LIMIT",
                reason=str(intent.get("entry_reason") or "entry_point_selector_limit"),
                price=price,
                limit_price=lp,
                confidence=0.80,
            )

        if limit_price > 0 or "mean_reversion" in signal_type or "pullback" in signal_type:
            lp = limit_price if limit_price > 0 else price
            return ExecutionDecision(
                action="LIMIT",
                symbol=symbol,
                side=side,
                qty=qty,
                order_type="LIMIT",
                reason="pullback_or_mean_reversion_limit",
                price=price,
                limit_price=lp,
                confidence=0.65,
            )

        return self._skip(symbol, side, qty, price, "no_execution_pattern")

    @staticmethod
    def _num(value: Any, default: float) -> float:
        try:
            if value is None or value == "":
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    def _spread_pct(self, market_state: dict[str, Any]) -> float | None:
        bid = self._num(market_state.get("bid"), 0.0)
        ask = self._num(market_state.get("ask"), 0.0)
        last = self._num(market_state.get("last"), 0.0)
        if bid <= 0 or ask <= 0 or ask < bid:
            return None
        base = last if last > 0 else (ask + bid) / 2.0
        if base <= 0:
            return None
        return (ask - bid) / base

    @staticmethod
    def _skip(symbol: str, side: str, qty: float, price: float | None, reason: str) -> ExecutionDecision:
        return ExecutionDecision(
            action="SKIP",
            symbol=symbol,
            side=side,
            qty=qty,
            order_type="NONE",
            reason=reason,
            price=price,
            confidence=0.0,
        )
