from __future__ import annotations

from dataclasses import dataclass


VALID_EXECUTION_TRANSITIONS = {
    "READY": {"RESERVED", "REJECTED", "ARCHIVED"},
    "RESERVED": {"SENDING", "SENT", "REJECTED", "ARCHIVED"},
    "SENDING": {"SENT", "FILLED", "REJECTED", "RECONCILE_REQUIRED"},
    "SENT": {"ACK", "FILLED", "REJECTED", "CANCELLED", "RECONCILE_REQUIRED"},
    "ACK": {"PARTIAL_FILL", "FILLED", "CANCELLED", "REJECTED", "RECONCILE_REQUIRED"},
    "PARTIAL_FILL": {"PARTIAL_FILL", "FILLED", "CANCELLED", "RECONCILE_REQUIRED"},
    "FILLED": {"CLOSED"},
    "CLOSED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
    "ARCHIVED": set(),
    "RECONCILE_REQUIRED": {"ACK", "FILLED", "CANCELLED", "REJECTED"},
}


@dataclass(frozen=True)
class ExecutionIntentFSMDecision:
    allowed: bool
    previous_state: str
    next_state: str
    reason: str


class ExecutionIntentFSM:
    """Русский комментарий: единый FSM для execution_intents.intent_state."""

    def validate(
        self,
        *,
        previous_state: str,
        next_state: str,
    ) -> ExecutionIntentFSMDecision:
        prev = str(previous_state or "").upper()
        nxt = str(next_state or "").upper()

        if prev == nxt:
            return ExecutionIntentFSMDecision(
                allowed=True,
                previous_state=prev,
                next_state=nxt,
                reason="same_state_noop",
            )

        if prev not in VALID_EXECUTION_TRANSITIONS:
            return ExecutionIntentFSMDecision(
                allowed=False,
                previous_state=prev,
                next_state=nxt,
                reason=f"unknown_previous_state:{prev}",
            )

        if nxt not in VALID_EXECUTION_TRANSITIONS[prev]:
            return ExecutionIntentFSMDecision(
                allowed=False,
                previous_state=prev,
                next_state=nxt,
                reason=f"invalid_transition:{prev}->{nxt}",
            )

        return ExecutionIntentFSMDecision(
            allowed=True,
            previous_state=prev,
            next_state=nxt,
            reason="transition_allowed",
        )
