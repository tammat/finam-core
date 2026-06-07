from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgTimeExitHoldBucketDecisionV1:
    allowed: bool
    action: str
    reason: str


class NgTimeExitHoldBucketPolicyV1:
    """
    Русский комментарий:
    Policy v1 для NG time_exit.

    Основание:
    trusted decomposition показал, что time_exit в 30-60 минут имеет
    отрицательное expectancy и PF около 0.05.
    Поэтому отрицательный time_exit до 60 минут блокируем/откладываем.
    """

    def evaluate(
        self,
        *,
        root_symbol: str,
        exit_reason: str,
        hold_seconds: float,
        unrealized_pnl: float,
    ) -> NgTimeExitHoldBucketDecisionV1:
        root = str(root_symbol or "").upper()
        reason = str(exit_reason or "").lower()
        hold = float(hold_seconds or 0.0)
        pnl = float(unrealized_pnl or 0.0)

        if root != "NG":
            return NgTimeExitHoldBucketDecisionV1(
                allowed=True,
                action="PASS",
                reason="not_ng",
            )

        if reason != "time_exit":
            return NgTimeExitHoldBucketDecisionV1(
                allowed=True,
                action="PASS",
                reason="not_time_exit",
            )

        if pnl >= 0:
            return NgTimeExitHoldBucketDecisionV1(
                allowed=True,
                action="ALLOW",
                reason="ng_time_exit_non_negative_pnl",
            )

        if hold < 3600:
            return NgTimeExitHoldBucketDecisionV1(
                allowed=False,
                action="EXTEND_HOLD",
                reason="ng_time_exit_negative_pnl_under_60m_block",
            )

        return NgTimeExitHoldBucketDecisionV1(
            allowed=True,
            action="ALLOW",
            reason="ng_time_exit_negative_pnl_after_60m_allowed",
        )
