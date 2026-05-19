from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderStateSyncDecision:
    intent_state: str
    reason: str


class RealOrderStateSynchronizer:
    """Русский комментарий: маппит состояние заявки брокера в execution_intents."""

    def map_broker_status(self, *, broker_status: str) -> OrderStateSyncDecision:
        status = str(broker_status or "").upper()

        if status in {"NEW", "ACTIVE", "WORKING", "ACCEPTED"}:
            return OrderStateSyncDecision("ACK", f"broker_status={status}")

        if status in {"PARTIAL", "PARTIALLY_FILLED", "PARTIAL_FILL"}:
            return OrderStateSyncDecision("PARTIAL_FILL", f"broker_status={status}")

        if status in {"FILLED", "DONE", "EXECUTED"}:
            return OrderStateSyncDecision("FILLED", f"broker_status={status}")

        if status in {"CANCELLED", "CANCELED"}:
            return OrderStateSyncDecision("CANCELLED", f"broker_status={status}")

        if status in {"REJECTED", "FAILED", "ERROR"}:
            return OrderStateSyncDecision("REJECTED", f"broker_status={status}")

        return OrderStateSyncDecision("SENT", f"broker_status_unknown={status}")
