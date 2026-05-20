from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrailingExitDecision:
    exit_required: bool
    stop_price: float
    reason: str


class TrailingExitPolicy:
    """Русский комментарий: простой synthetic trailing для long-позиции."""

    def decide(
        self,
        *,
        avg_price: float,
        current_price: float,
        trail_pct: float,
    ) -> TrailingExitDecision:
        if avg_price <= 0 or current_price <= 0:
            return TrailingExitDecision(False, 0.0, "invalid_price")

        stop_price = round(current_price * (1.0 - trail_pct), 4)

        if current_price <= stop_price:
            return TrailingExitDecision(True, stop_price, "trailing_stop_hit")

        return TrailingExitDecision(False, stop_price, "trailing_hold")
