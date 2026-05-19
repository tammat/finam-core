from __future__ import annotations

from dataclasses import dataclass


VALID_TRANSITIONS = {
    "READY": {"RESERVED", "REJECTED", "ARCHIVED"},
    "RESERVED": {"SENT", "REJECTED", "ARCHIVED"},
    "SENT": {"ACK", "REJECTED", "CANCELLED"},
    "ACK": {"PARTIAL_FILL", "FILLED", "CANCELLED", "REJECTED"},
    "PARTIAL_FILL": {"PARTIAL_FILL", "FILLED", "CANCELLED"},
    "FILLED": {"CLOSED"},
    "CLOSED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
    "ARCHIVED": set(),
}


@dataclass(frozen=True)
class LifecycleTransitionDecision:
    allowed: bool
    previous_state: str
    next_state: str
    reason: str


class ExecutionLifecycleDeterminism:
    """Русский комментарий: запрещает impossible lifecycle transitions."""

    def validate_transition(
        self,
        *,
        previous_state: str,
        next_state: str,
    ) -> LifecycleTransitionDecision:

        prev = str(previous_state or "").upper()
        nxt = str(next_state or "").upper()

        if prev not in VALID_TRANSITIONS:
            return LifecycleTransitionDecision(
                allowed=False,
                previous_state=prev,
                next_state=nxt,
                reason=f"unknown_previous_state:{prev}",
            )

        allowed_next = VALID_TRANSITIONS[prev]

        if nxt not in allowed_next:
            return LifecycleTransitionDecision(
                allowed=False,
                previous_state=prev,
                next_state=nxt,
                reason=f"invalid_transition:{prev}->{nxt}",
            )

        return LifecycleTransitionDecision(
            allowed=True,
            previous_state=prev,
            next_state=nxt,
            reason="transition_allowed",
        )
