from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalLifecycleDecision:
    state: str
    close_reason: str | None = None


class SignalLifecycleEngine:
    """Русский комментарий: управляет жизненным циклом торгового сигнала."""

    def evaluate(
        self,
        *,
        state: str,
        current_price: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> SignalLifecycleDecision:
        if state in {"CLOSED", "EXPIRED", "CANCELLED"}:
            return SignalLifecycleDecision(state=state)

        if current_price <= 0:
            return SignalLifecycleDecision(state=state)

        if state in {"NEW", "ACTIVE"}:
            if current_price >= entry_price:
                return SignalLifecycleDecision(state="TRIGGERED")

            return SignalLifecycleDecision(state="ACTIVE")

        if state == "TRIGGERED":
            if current_price <= stop_loss:
                return SignalLifecycleDecision(state="CLOSED", close_reason="STOP_LOSS")

            if current_price >= take_profit:
                return SignalLifecycleDecision(state="CLOSED", close_reason="TAKE_PROFIT")

            return SignalLifecycleDecision(state="TRIGGERED")

        return SignalLifecycleDecision(state=state)
