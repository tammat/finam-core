"""Read-only mapping research-family → существующий research executor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetedResearchExecutorDecisionV1:
    research_family: str
    executor_code: str | None
    handler: str | None
    state_code: str
    reason_code: str


def resolve_targeted_research_executor_v1(
    research_family: str,
) -> TargetedResearchExecutorDecisionV1:
    family = str(research_family or "").strip().upper()

    if family == "ECONOMIC_OOS":
        return TargetedResearchExecutorDecisionV1(
            research_family=family,
            executor_code="WALKFORWARD",
            handler="src/scripts/run_checkpointed_walkforward_v4.py",
            state_code="REUSE_EXISTING_EXECUTOR",
            reason_code="AUTONOMOUS_WALKFORWARD_EXECUTOR_AVAILABLE",
        )

    if family == "EXIT_OOS":
        return TargetedResearchExecutorDecisionV1(
            research_family=family,
            executor_code="TARGETED_ENTRY_EXIT_OOS_V1",
            handler="src/scripts/run_targeted_entry_exit_oos_v1.py",
            state_code="REUSE_EXISTING_EXECUTOR",
            reason_code="TARGETED_ENTRY_EXIT_OOS_EXECUTOR_AVAILABLE",
        )

    return TargetedResearchExecutorDecisionV1(
        research_family=family,
        executor_code=None,
        handler=None,
        state_code="UNRESOLVED",
        reason_code="NO_TARGETED_RESEARCH_EXECUTOR_MAPPING",
    )
