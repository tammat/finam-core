from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeExitGovernanceDecisionV1:
    allowed: bool
    mode: str
    reason: str
    action: str


class TimeExitGovernanceV1:
    """Русский комментарий: policy-класс для управления time_exit без прямого исполнения ордеров."""

    def __init__(self, mode: str = "shadow") -> None:
        self.mode = (mode or "shadow").lower()

    def evaluate(
        self,
        *,
        root_symbol: str,
        side: str,
        unrealized_pnl: float | None = None,
        reason: str = "",
    ) -> TimeExitGovernanceDecisionV1:
        root = (root_symbol or "").upper()
        side_u = (side or "").upper()
        reason_u = (reason or "").lower()
        pnl = float(unrealized_pnl or 0.0)

        if reason_u != "time_exit":
            return TimeExitGovernanceDecisionV1(
                allowed=True,
                mode=self.mode,
                reason="not_time_exit",
                action="PASS",
            )

        if root == "BR":
            return TimeExitGovernanceDecisionV1(
                allowed=False,
                mode=self.mode,
                reason="br_time_exit_noise_block_or_shadow",
                action="SHADOW_BLOCK",
            )

        if root == "NG":
            if pnl >= 0:
                return TimeExitGovernanceDecisionV1(
                    allowed=True,
                    mode=self.mode,
                    reason="ng_time_exit_allowed_only_non_negative_pnl",
                    action="ALLOW",
                )

            return TimeExitGovernanceDecisionV1(
                allowed=False,
                mode=self.mode,
                reason="ng_time_exit_negative_pnl_block_or_shadow",
                action="SHADOW_BLOCK",
            )

        return TimeExitGovernanceDecisionV1(
            allowed=True,
            mode=self.mode,
            reason="unknown_root_fail_open",
            action="PASS",
        )
