# -*- coding: utf-8 -*-
"""
Order ACK model.

Русский комментарий: фиксируем факт ответа брокера после PlaceOrder.
Без ACK order не считается подтверждённым.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrderAck:
    accepted: bool
    symbol: str
    side: str
    qty: float
    order_id: str | None
    status: str
    reason: str | None = None
    raw: dict[str, Any] | None = None
