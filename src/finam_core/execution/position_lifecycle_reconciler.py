from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifecycleReconciliationDecision:
    action: str
    symbol: str
    reason: str
    expected_qty: float
    actual_qty: float


class PositionLifecycleReconciler:
    """
    Русский комментарий:
    Сверяет persistent lifecycle state с фактической позицией.

    Если lifecycle считает, что позиция есть, а фактическая позиция = 0,
    state должен быть очищен/закрыт.
    """

    def reconcile(
        self,
        *,
        symbol: str,
        expected_remaining_qty: float | None,
        actual_qty: float | None,
    ) -> LifecycleReconciliationDecision:
        expected = float(expected_remaining_qty or 0.0)
        actual = float(actual_qty or 0.0)

        if abs(expected) > 1e-9 and abs(actual) <= 1e-9:
            return LifecycleReconciliationDecision(
                action="CLEAR_STATE",
                symbol=symbol,
                reason="position_closed_but_lifecycle_state_active",
                expected_qty=expected,
                actual_qty=actual,
            )

        if abs(expected - actual) > 1e-9:
            return LifecycleReconciliationDecision(
                action="UPDATE_REMAINING_QTY",
                symbol=symbol,
                reason="remaining_qty_mismatch",
                expected_qty=expected,
                actual_qty=actual,
            )

        return LifecycleReconciliationDecision(
            action="OK",
            symbol=symbol,
            reason="state_matches_position",
            expected_qty=expected,
            actual_qty=actual,
        )
