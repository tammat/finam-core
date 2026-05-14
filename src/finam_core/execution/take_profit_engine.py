from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TakeProfitDecision:
    action: str
    qty_to_close: float
    take_price: float | None
    reason: str


class TakeProfitEngine:
    def evaluate_long(self, *, qty: float, entry_price: float, current_price: float, stop_price: float) -> TakeProfitDecision:
        if qty <= 0 or entry_price <= 0 or current_price <= 0 or stop_price <= 0:
            return TakeProfitDecision("HOLD", 0.0, None, "invalid_input")

        risk = entry_price - stop_price
        if risk <= 0:
            return TakeProfitDecision("HOLD", 0.0, None, "invalid_risk")

        r_multiple = (current_price - entry_price) / risk

        if qty < 2:
            if r_multiple >= 2.0:
                return TakeProfitDecision("CLOSE_FULL", qty, round(entry_price + 2.0 * risk, 2), "single_qty_take_profit_2r")
            return TakeProfitDecision("HOLD", 0.0, round(entry_price + 2.0 * risk, 2), "single_qty_wait_tp")

        if r_multiple >= 2.0:
            return TakeProfitDecision("PARTIAL_CLOSE", max(1.0, round(qty * 0.5, 2)), round(entry_price + 2.0 * risk, 2), "multi_qty_take_half_2r")

        if r_multiple >= 1.0:
            return TakeProfitDecision("PARTIAL_CLOSE", max(1.0, round(qty * 0.25, 2)), round(entry_price + 1.0 * risk, 2), "multi_qty_take_quarter_1r")

        return TakeProfitDecision("HOLD", 0.0, round(entry_price + 1.0 * risk, 2), "multi_qty_wait_tp")
