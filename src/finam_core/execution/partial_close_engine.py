from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PartialCloseDecision:
    action: str
    qty_to_close: float
    remaining_qty: float
    stage: str
    reason: str


class PartialCloseEngine:
    """
    Русский комментарий:
    Расчёт частичного закрытия позиции.

    qty < 2:
      частичное закрытие невозможно.

    qty >= 2:
      TP1 закрывает 25%;
      TP2 закрывает 50%;
      остаток остаётся под trailing/profit-lock.
    """

    def evaluate_long(
        self,
        *,
        qty: float,
        entry_price: float,
        current_price: float,
        stop_price: float,
        tp1_done: bool = False,
        tp2_done: bool = False,
    ) -> PartialCloseDecision:
        if qty <= 0 or entry_price <= 0 or current_price <= 0 or stop_price <= 0:
            return PartialCloseDecision("HOLD", 0.0, qty, "NONE", "invalid_input")

        if qty < 2:
            return PartialCloseDecision("HOLD", 0.0, qty, "NONE", "single_qty_no_partial")

        risk = entry_price - stop_price
        if risk <= 0:
            return PartialCloseDecision("HOLD", 0.0, qty, "NONE", "invalid_risk")

        r_multiple = (current_price - entry_price) / risk

        if r_multiple >= 2.0 and not tp2_done:
            qty_to_close = max(1.0, round(qty * 0.50, 2))
            qty_to_close = min(qty_to_close, qty)

            return PartialCloseDecision(
                action="PARTIAL_CLOSE",
                qty_to_close=qty_to_close,
                remaining_qty=round(qty - qty_to_close, 2),
                stage="TP2",
                reason="partial_close_tp2_2r",
            )

        if r_multiple >= 1.0 and not tp1_done:
            qty_to_close = max(1.0, round(qty * 0.25, 2))
            qty_to_close = min(qty_to_close, qty)

            return PartialCloseDecision(
                action="PARTIAL_CLOSE",
                qty_to_close=qty_to_close,
                remaining_qty=round(qty - qty_to_close, 2),
                stage="TP1",
                reason="partial_close_tp1_1r",
            )

        return PartialCloseDecision("HOLD", 0.0, qty, "NONE", "no_partial_close_signal")
