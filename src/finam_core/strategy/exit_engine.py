# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    reason: str
    stop_price: float | None = None


class ExitEngine:
    """Русский комментарий: ExitEngine только принимает решение о выходе, заявки не отправляет."""

    def __init__(
        self,
        max_bars_in_trade: int = 20,
        breakeven_atr_k: float = 1.0,
        trailing_atr_k: float = 1.5,
        stall_atr_k: float = 0.2,
        min_bars_before_stall_exit: int = 3,
        enable_stall_exit: bool = True,
    ) -> None:
        self.max_bars_in_trade = int(max_bars_in_trade)
        self.breakeven_atr_k = float(breakeven_atr_k)
        self.trailing_atr_k = float(trailing_atr_k)
        self.stall_atr_k = float(stall_atr_k)
        # Русский комментарий: stall-exit не должен закрывать только что открытую позицию.
        self.min_bars_before_stall_exit = int(min_bars_before_stall_exit)
        self.enable_stall_exit = bool(enable_stall_exit)

    def evaluate(
        self,
        *,
        side: str,
        entry_price: float,
        current_price: float,
        atr: float,
        bars_held: int,
        prev_close: float | None = None,
        current_stop: float | None = None,
    ) -> ExitDecision:
        side = side.upper()
        entry = float(entry_price)
        price = float(current_price)
        atr = float(atr)

        if atr <= 0:
            return ExitDecision(False, "no_atr", current_stop)

        if side == "BUY":
            profit = price - entry

            if current_stop is not None and price <= current_stop:
                return ExitDecision(True, "stop_loss_long", current_stop)

            if bars_held >= self.max_bars_in_trade:
                return ExitDecision(True, "time_exit", current_stop)

            stop = current_stop

            if profit >= self.breakeven_atr_k * atr:
                stop = max(stop or entry, entry)

            if profit >= self.trailing_atr_k * atr:
                stop = max(stop or entry, price - self.trailing_atr_k * atr)

            if (
                self.enable_stall_exit
                and
                bars_held >= self.min_bars_before_stall_exit
                and prev_close is not None
                and abs(price - float(prev_close)) < self.stall_atr_k * atr
                and profit > 0
            ):
                return ExitDecision(True, "stall_exit_long", stop)

            return ExitDecision(False, "hold_long", stop)

        if side == "SELL":
            profit = entry - price

            if current_stop is not None and price >= current_stop:
                return ExitDecision(True, "stop_loss_short", current_stop)

            if bars_held >= self.max_bars_in_trade:
                return ExitDecision(True, "time_exit", current_stop)

            stop = current_stop

            if profit >= self.breakeven_atr_k * atr:
                stop = min(stop or entry, entry)

            if profit >= self.trailing_atr_k * atr:
                stop = min(stop or entry, price + self.trailing_atr_k * atr)

            if (
                self.enable_stall_exit
                and
                bars_held >= self.min_bars_before_stall_exit
                and prev_close is not None
                and abs(price - float(prev_close)) < self.stall_atr_k * atr
                and profit > 0
            ):
                return ExitDecision(True, "stall_exit_short", stop)

            return ExitDecision(False, "hold_short", stop)

        return ExitDecision(False, "unknown_side", current_stop)

# =========================================================
# === EXIT STATE MACHINE / NO DUPLICATE EXIT REQUESTS
# =========================================================

from dataclasses import dataclass, field
import time


@dataclass
class ExitOrderState:
    """Русский комментарий: состояние exit-заявки по одному инструменту."""
    symbol: str
    position_qty: float = 0.0
    requested_side: str | None = None
    requested_qty: float = 0.0
    reason: str | None = None
    status: str = "IDLE"  # IDLE -> REQUESTED -> FILLED
    requested_at: float = 0.0
    ttl_sec: float = 30.0

    def active(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self.status == "REQUESTED" and (now - self.requested_at) <= self.ttl_sec


@dataclass
class ExitStateMachine:
    """Русский комментарий: первый exit разрешается сразу, TTL гасит только дубли."""
    ttl_sec: float = 30.0
    states: dict[str, ExitOrderState] = field(default_factory=dict)

    def state_for(self, symbol: str) -> ExitOrderState:
        if symbol not in self.states:
            self.states[symbol] = ExitOrderState(symbol=symbol, ttl_sec=self.ttl_sec)
        return self.states[symbol]

    def on_position(self, symbol: str, qty: float) -> None:
        st = self.state_for(symbol)
        qty = float(qty or 0.0)
        if qty == 0.0 or abs(st.position_qty - qty) > 1e-9:
            st.status = "IDLE"
            st.requested_side = None
            st.requested_qty = 0.0
            st.reason = None
            st.requested_at = 0.0
        st.position_qty = qty

    def allow_request(self, symbol: str, side: str, qty: float, reason: str) -> tuple[bool, str]:
        st = self.state_for(symbol)
        now = time.time()

        if st.status == "REQUESTED" and not st.active(now):
            st.status = "IDLE"

        same = (
            st.requested_side == side
            and abs(float(st.requested_qty or 0.0) - float(qty or 0.0)) <= 1e-9
            and st.reason == reason
        )

        if st.active(now) and same:
            return False, "duplicate_exit_request_active"

        st.status = "REQUESTED"
        st.requested_side = side
        st.requested_qty = float(qty or 0.0)
        st.reason = reason
        st.requested_at = now
        return True, "exit_request_allowed"

    def on_fill(self, symbol: str) -> None:
        self.state_for(symbol).status = "FILLED"

    def on_failed(self, symbol: str) -> None:
        """Освобождает exit-заявку, которая не дошла до подтверждённого fill."""
        st = self.state_for(symbol)
        st.status = "IDLE"
        st.requested_side = None
        st.requested_qty = 0.0
        st.reason = None
        st.requested_at = 0.0
