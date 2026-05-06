# -*- coding: utf-8 -*-
"""
Русский комментарий:
BrokerOrderStateMachine.
Отвечает за жизненный цикл реальной заявки.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


VALID_STATES = {
    "NEW",
    "SUBMITTED",
    "ACCEPTED",
    "PARTIAL_FILLED",
    "FILLED",
    "REJECTED",
    "CANCEL_REQUESTED",
    "CANCELLED",
    "EXPIRED",
    "STALE",
}


@dataclass
class OrderState:
    order_id: str
    symbol: str
    side: str
    qty: float

    filled_qty: float = 0.0
    avg_fill_price: float = 0.0

    state: str = "NEW"

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    reason: Optional[str] = None

    def transition(self, new_state: str) -> None:
        if new_state not in VALID_STATES:
            raise ValueError(f"invalid_state={new_state}")

        self.state = new_state
        self.updated_at = datetime.utcnow()

    def on_submitted(self) -> None:
        self.transition("SUBMITTED")

    def on_accepted(self) -> None:
        self.transition("ACCEPTED")

    def on_partial_fill(self, fill_qty: float, fill_price: float) -> None:
        total_value = (
            self.avg_fill_price * self.filled_qty
            + fill_price * fill_qty
        )

        self.filled_qty += fill_qty

        if self.filled_qty > 0:
            self.avg_fill_price = total_value / self.filled_qty

        if self.filled_qty >= self.qty:
            self.transition("FILLED")
        else:
            self.transition("PARTIAL_FILLED")

    def on_rejected(self, reason: str) -> None:
        self.reason = reason
        self.transition("REJECTED")

    def on_cancel_requested(self) -> None:
        self.transition("CANCEL_REQUESTED")

    def on_cancelled(self) -> None:
        self.transition("CANCELLED")

    def on_expired(self) -> None:
        self.transition("EXPIRED")

    def on_stale(self) -> None:
        self.transition("STALE")