# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

from finam_core.execution.protective_order_link_repository import ProtectiveOrderLinkRepository


@dataclass(frozen=True)
class ProtectiveDuplicateDecision:
    allowed: bool
    reason: str
    entry_order_id: str
    protective_type: str


class ProtectiveDuplicateGate:
    def __init__(self, repository: ProtectiveOrderLinkRepository | None = None) -> None:
        self.repository = repository or ProtectiveOrderLinkRepository()

    def check(self, *, entry_order_id: str, protective_type: str) -> ProtectiveDuplicateDecision:
        if not entry_order_id:
            return ProtectiveDuplicateDecision(False, "PROTECTIVE_ENTRY_ORDER_ID_MISSING", entry_order_id, protective_type)

        if protective_type not in ("stop", "take"):
            return ProtectiveDuplicateDecision(False, "PROTECTIVE_TYPE_INVALID", entry_order_id, protective_type)

        if self.repository.has_existing_protective_order(
            entry_order_id=entry_order_id,
            protective_type=protective_type,
        ):
            return ProtectiveDuplicateDecision(False, "PROTECTIVE_DUPLICATE_BLOCK", entry_order_id, protective_type)

        return ProtectiveDuplicateDecision(True, "PROTECTIVE_DUPLICATE_OK", entry_order_id, protective_type)
