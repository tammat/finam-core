# -*- coding: utf-8 -*-
"""
ProtectiveOrderLink — связь entry order с защитными stop/take заявками.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProtectiveOrderLink:
    symbol: str
    side: str
    qty: float
    entry_order_id: str
    stop_order_id: str | None = None
    take_order_id: str | None = None
    status: str = "OPEN"
    source: str = "finam_core"
    raw: dict[str, Any] | None = None

    @property
    def has_stop(self) -> bool:
        return bool(self.stop_order_id)

    @property
    def has_take(self) -> bool:
        return bool(self.take_order_id)

    @property
    def is_protected(self) -> bool:
        return self.has_stop or self.has_take
