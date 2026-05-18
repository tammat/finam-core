from __future__ import annotations

from dataclasses import dataclass

from finam_core.runtime.active_policy_reader import ActivePolicyDecision


@dataclass(frozen=True)
class RuntimePolicyMode:
    selected_mode: str
    apply_adaptive_risk: bool
    allow_blocking: bool
    allow_multiplier: bool
    reason: str


class RuntimePolicyModeResolver:
    """Русский комментарий: переводит active policy decision в режим поведения runtime."""

    def resolve(self, decision: ActivePolicyDecision | None) -> RuntimePolicyMode:
        if decision is None:
            return RuntimePolicyMode(
                selected_mode="BASE",
                apply_adaptive_risk=False,
                allow_blocking=False,
                allow_multiplier=False,
                reason="active_policy_not_found",
            )

        mode = str(decision.selected_mode or "BASE").upper()

        if mode == "BASE":
            return RuntimePolicyMode(
                selected_mode="BASE",
                apply_adaptive_risk=False,
                allow_blocking=False,
                allow_multiplier=False,
                reason=f"policy_mode=BASE;decision_id={decision.decision_id}",
            )

        if mode == "LIMITED":
            return RuntimePolicyMode(
                selected_mode="LIMITED",
                apply_adaptive_risk=True,
                allow_blocking=False,
                allow_multiplier=True,
                reason=f"policy_mode=LIMITED;decision_id={decision.decision_id}",
            )

        if mode == "SELECTIVE":
            return RuntimePolicyMode(
                selected_mode="SELECTIVE",
                apply_adaptive_risk=True,
                allow_blocking=True,
                allow_multiplier=True,
                reason=f"policy_mode=SELECTIVE;decision_id={decision.decision_id}",
            )

        return RuntimePolicyMode(
            selected_mode=mode,
            apply_adaptive_risk=False,
            allow_blocking=False,
            allow_multiplier=False,
            reason=f"unknown_policy_mode={mode};decision_id={decision.decision_id}",
        )
