from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.oms.order_journal import OmsOrderJournal


@dataclass(frozen=True)
class OmsDispatchDecision:
    allowed: bool
    client_order_id: str
    reason: str


class OmsDispatchGuard:
    """Русский комментарий: защита ExecutionDispatcher от повторной отправки одной заявки."""

    def __init__(self, journal: OmsOrderJournal | None = None) -> None:
        self.journal = journal or OmsOrderJournal()

    def prepare(self, intent: dict[str, Any]) -> OmsDispatchDecision:
        symbol = str(intent.get("symbol"))
        side = str(intent.get("side"))
        qty = float(intent.get("qty") or 0.0)
        price_raw = intent.get("price")
        price = None if price_raw is None else float(price_raw)

        client_order_id = intent.get("client_order_id")
        if not client_order_id:
            client_order_id = self.journal.build_client_order_id(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                strategy=str(intent.get("strategy") or intent.get("source") or "execution_dispatcher"),
                ts_bucket=str(intent.get("ts") or intent.get("timestamp") or "manual"),
            )
            intent["client_order_id"] = client_order_id

        created, _record = self.journal.create_if_absent(
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            order_type=str(intent.get("order_type") or "MARKET"),
            status="CREATED",
            source="execution_dispatcher",
            payload=dict(intent),
        )

        if not created:
            return OmsDispatchDecision(
                allowed=False,
                client_order_id=client_order_id,
                reason="duplicate_client_order_id",
            )

        return OmsDispatchDecision(
            allowed=True,
            client_order_id=client_order_id,
            reason="created",
        )

    def mark_sent(self, *, client_order_id: str, broker_order_id: str | None = None) -> None:
        self.journal.update_status(
            client_order_id=client_order_id,
            status="SENT",
            broker_order_id=broker_order_id,
        )
