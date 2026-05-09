from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


TERMINAL_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
    OrderStatus.FAILED,
}


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {
        OrderStatus.SENT,
        OrderStatus.REJECTED,
        OrderStatus.FAILED,
    },
    OrderStatus.SENT: {
        OrderStatus.ACCEPTED,
        OrderStatus.REJECTED,
        OrderStatus.FAILED,
        OrderStatus.CANCEL_REQUESTED,
    },
    OrderStatus.ACCEPTED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_REQUESTED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_REQUESTED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.FAILED,
    },
    OrderStatus.CANCEL_REQUESTED: {
        OrderStatus.CANCELLED,
        OrderStatus.FILLED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FAILED,
    },
    OrderStatus.FILLED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REJECTED: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.FAILED: set(),
}


@dataclass(frozen=True)
class OrderTransitionResult:
    allowed: bool
    old_status: OrderStatus
    new_status: OrderStatus
    reason: str


class OrderStateMachine:
    """Русский комментарий: строгая FSM для жизненного цикла заявки OMS."""

    @staticmethod
    def normalize(status: str | OrderStatus) -> OrderStatus:
        if isinstance(status, OrderStatus):
            return status
        try:
            return OrderStatus(str(status).strip().upper())
        except Exception as exc:
            raise ValueError(f"Unknown order status: {status}") from exc

    def is_terminal(self, status: str | OrderStatus) -> bool:
        return self.normalize(status) in TERMINAL_STATUSES

    def can_transition(
        self,
        old_status: str | OrderStatus,
        new_status: str | OrderStatus,
    ) -> bool:
        old = self.normalize(old_status)
        new = self.normalize(new_status)

        if old == new:
            return True

        return new in ALLOWED_TRANSITIONS.get(old, set())

    def validate_transition(
        self,
        old_status: str | OrderStatus,
        new_status: str | OrderStatus,
    ) -> OrderTransitionResult:
        old = self.normalize(old_status)
        new = self.normalize(new_status)

        if old == new:
            return OrderTransitionResult(
                allowed=True,
                old_status=old,
                new_status=new,
                reason="same_status",
            )

        if self.can_transition(old, new):
            return OrderTransitionResult(
                allowed=True,
                old_status=old,
                new_status=new,
                reason="allowed",
            )

        return OrderTransitionResult(
            allowed=False,
            old_status=old,
            new_status=new,
            reason=f"invalid_transition:{old.value}->{new.value}",
        )
