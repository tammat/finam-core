from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfitLockDecision:
    action: str
    qty_to_close: float
    new_stop: float | None
    reason: str


class ProfitLockEngine:
    """
    Русский комментарий:
    Profit-lock сопровождение позиции.

    qty = 1:
      partial close невозможен, двигаем stop.

    qty > 1:
      можно закрыть часть на TP1, остаток вести trailing/breakeven.
    """

    def evaluate_long(
        self,
        *,
        qty: float,
        entry_price: float,
        current_price: float,
        stop_price: float,
    ) -> ProfitLockDecision:
        if qty <= 0 or entry_price <= 0 or current_price <= 0 or stop_price <= 0:
            return ProfitLockDecision("HOLD", 0.0, None, "invalid_input")

        risk = entry_price - stop_price
        if risk <= 0:
            return ProfitLockDecision("HOLD", 0.0, None, "invalid_risk")

        r_multiple = (current_price - entry_price) / risk

        # 1 позиция: только защита прибыли через stop.
        if qty < 2:
            if r_multiple >= 2.0:
                return ProfitLockDecision(
                    "MOVE_STOP",
                    0.0,
                    round(entry_price + 0.75 * risk, 2),
                    "single_qty_lock_0_75r",
                )

            if r_multiple >= 1.5:
                return ProfitLockDecision(
                    "MOVE_STOP",
                    0.0,
                    round(entry_price + 0.5 * risk, 2),
                    "single_qty_lock_0_5r",
                )

            if r_multiple >= 1.0:
                return ProfitLockDecision(
                    "MOVE_STOP",
                    0.0,
                    round(entry_price, 2),
                    "single_qty_breakeven",
                )

            return ProfitLockDecision("HOLD", 0.0, None, "single_qty_wait")

        # Более 1 позиции: частичная фиксация + stop на остаток.
        if r_multiple >= 2.0:
            return ProfitLockDecision(
                "PARTIAL_CLOSE_AND_MOVE_STOP",
                max(1.0, round(qty * 0.5, 2)),
                round(entry_price + 0.5 * risk, 2),
                "multi_qty_take_half_lock_0_5r",
            )

        if r_multiple >= 1.0:
            return ProfitLockDecision(
                "MOVE_STOP",
                0.0,
                round(entry_price, 2),
                "multi_qty_breakeven",
            )

        return ProfitLockDecision("HOLD", 0.0, None, "multi_qty_wait")
