from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionLifecycleDecision:
    action: str
    new_stop: float
    reason: str


class PositionLifecycleManager:
    """Русский комментарий: управляет жизненным циклом открытой позиции."""

    def evaluate(
        self,
        *,
        side: str,
        entry_price: float,
        current_price: float,
        current_stop: float,
        take_profit: float,
        breakeven_done: bool = False,
    ) -> PositionLifecycleDecision:
        if entry_price <= 0 or current_price <= 0:
            return PositionLifecycleDecision("HOLD", current_stop, "invalid_price")

        side = side.upper()

        if side != "BUY":
            return PositionLifecycleDecision("HOLD", current_stop, "only_buy_supported_v1")

        if current_price <= current_stop:
            return PositionLifecycleDecision("CLOSE", current_stop, "stop_loss_hit")

        if current_price >= take_profit:
            return PositionLifecycleDecision("CLOSE", current_stop, "take_profit_hit")

        profit_pct = (current_price - entry_price) / entry_price

        if profit_pct >= 0.01 and not breakeven_done:
            return PositionLifecycleDecision(
                "MOVE_STOP",
                entry_price,
                "move_stop_to_breakeven",
            )

        if profit_pct >= 0.02:
            trailing_stop = current_price * 0.99
            if trailing_stop > current_stop:
                return PositionLifecycleDecision(
                    "MOVE_STOP",
                    trailing_stop,
                    "trailing_stop_update",
                )

        return PositionLifecycleDecision("HOLD", current_stop, "hold")
