from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionIntentDecision:
    next_state: str
    reason: str


class ExecutionIntentRouter:
    """Русский комментарий: lifecycle router execution intent."""

    VALID_STATES = {
        "READY",
        "RESERVED",
        "SENT",
        "ACK",
        "PARTIAL_FILL",
        "FILLED",
        "CANCELLED",
        "REJECTED",
    }

    def transition(
        self,
        *,
        current_state: str,
        event: str,
    ) -> ExecutionIntentDecision:

        state = current_state.upper()
        evt = event.upper()

        if state not in self.VALID_STATES:
            return ExecutionIntentDecision(
                next_state="REJECTED",
                reason=f"invalid_state:{state}",
            )

        transitions = {
            ("READY", "RESERVE"): "RESERVED",
            ("RESERVED", "SEND"): "SENT",
            ("SENT", "ACK"): "ACK",
            ("ACK", "PARTIAL_FILL"): "PARTIAL_FILL",
            ("ACK", "FILL"): "FILLED",
            ("PARTIAL_FILL", "FILL"): "FILLED",
            ("READY", "CANCEL"): "CANCELLED",
            ("RESERVED", "CANCEL"): "CANCELLED",
            ("SENT", "REJECT"): "REJECTED",
            ("ACK", "REJECT"): "REJECTED",
        }

        next_state = transitions.get((state, evt))

        if next_state is None:
            return ExecutionIntentDecision(
                next_state=state,
                reason=f"transition_ignored:{state}:{evt}",
            )

        return ExecutionIntentDecision(
            next_state=next_state,
            reason=f"{state}->{next_state}",
        )
