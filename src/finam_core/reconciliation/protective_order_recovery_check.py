# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

from finam_core.execution.protective_order_link_repository import ProtectiveOrderLinkRepository


@dataclass(frozen=True)
class ProtectiveOrderRecoveryIssue:
    symbol: str
    side: str
    qty: float
    entry_order_id: str
    issue_type: str
    reason: str


class ProtectiveOrderRecoveryCheck:
    def __init__(self, repository: ProtectiveOrderLinkRepository | None = None) -> None:
        self.repository = repository or ProtectiveOrderLinkRepository()

    def check(self, *, limit: int = 100) -> list[ProtectiveOrderRecoveryIssue]:
        links = self.repository.list_open_unprotected(limit=limit)
        return [
            ProtectiveOrderRecoveryIssue(
                symbol=link.symbol,
                side=link.side,
                qty=link.qty,
                entry_order_id=link.entry_order_id,
                issue_type="PROTECTIVE_LINK_UNPROTECTED_ENTRY",
                reason="open_entry_has_no_stop_or_take_link",
            )
            for link in links
        ]
