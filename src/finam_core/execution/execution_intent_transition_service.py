from __future__ import annotations

from dataclasses import dataclass

from finam_core.execution.execution_intent_fsm import ExecutionIntentFSM
from finam_core.execution.execution_state_transition_logger import (
    ExecutionStateTransitionLogger,
)


@dataclass(frozen=True)
class ExecutionIntentTransitionResult:
    applied: bool
    intent_id: int
    previous_state: str
    next_state: str
    reason: str


class ExecutionIntentTransitionService:
    """Русский комментарий: единая точка изменения execution_intents.intent_state."""

    def __init__(self) -> None:
        self.fsm = ExecutionIntentFSM()
        self.logger = ExecutionStateTransitionLogger()

    def transition(
        self,
        cur,
        *,
        intent_id: int,
        next_state: str,
        reason: str,
    ) -> ExecutionIntentTransitionResult:
        cur.execute(
            """
            select intent_state
            from execution_intents
            where id = %s
            for update
            """,
            (intent_id,),
        )

        row = cur.fetchone()

        if row is None:
            return ExecutionIntentTransitionResult(
                applied=False,
                intent_id=intent_id,
                previous_state="UNKNOWN",
                next_state=str(next_state).upper(),
                reason="intent_not_found",
            )

        previous_state = str(row[0] or "").upper()
        normalized_next = str(next_state or "").upper()

        decision = self.fsm.validate(
            previous_state=previous_state,
            next_state=normalized_next,
        )

        if not decision.allowed:
            self.logger.log(
                cur,
                intent_id=intent_id,
                previous_state=previous_state,
                next_state=normalized_next,
                reason=f"ILLEGAL:{decision.reason};{reason}",
            )

            return ExecutionIntentTransitionResult(
                applied=False,
                intent_id=intent_id,
                previous_state=previous_state,
                next_state=normalized_next,
                reason=decision.reason,
            )

        cur.execute(
            """
            update execution_intents
            set
                intent_state = %s,
                reason = %s,
                updated_at = now()
            where id = %s
            """,
            (
                normalized_next,
                reason,
                intent_id,
            ),
        )

        self.logger.log(
            cur,
            intent_id=intent_id,
            previous_state=previous_state,
            next_state=normalized_next,
            reason=reason,
        )

        return ExecutionIntentTransitionResult(
            applied=True,
            intent_id=intent_id,
            previous_state=previous_state,
            next_state=normalized_next,
            reason=reason,
        )
