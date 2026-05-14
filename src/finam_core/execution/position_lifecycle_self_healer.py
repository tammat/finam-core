from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifecycleSelfHealingDecision:
    action: str
    reason: str
    should_delete_state: bool
    should_clear_trailing_cache: bool


class PositionLifecycleSelfHealer:
    """
    Русский комментарий:
    Self-healing слой lifecycle.

    Ничего не торгует.
    Только определяет, нужно ли очистить устаревшее состояние.
    """

    def evaluate(
        self,
        *,
        state_exists: bool,
        actual_qty: float,
        trailing_active: bool,
        current_stop: float | None,
    ) -> LifecycleSelfHealingDecision:
        actual = float(actual_qty or 0.0)

        if not state_exists:
            return LifecycleSelfHealingDecision(
                action="NOOP",
                reason="no_lifecycle_state",
                should_delete_state=False,
                should_clear_trailing_cache=False,
            )

        if abs(actual) <= 1e-9:
            return LifecycleSelfHealingDecision(
                action="DELETE_ORPHAN_STATE",
                reason="actual_position_is_zero",
                should_delete_state=True,
                should_clear_trailing_cache=True,
            )

        if trailing_active and (current_stop is None or float(current_stop or 0.0) <= 0):
            return LifecycleSelfHealingDecision(
                action="MARK_STALE_TRAILING",
                reason="trailing_active_without_valid_stop",
                should_delete_state=False,
                should_clear_trailing_cache=True,
            )

        return LifecycleSelfHealingDecision(
            action="OK",
            reason="lifecycle_state_is_consistent",
            should_delete_state=False,
            should_clear_trailing_cache=False,
        )
