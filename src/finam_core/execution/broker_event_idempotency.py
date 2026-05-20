from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerEventIdempotencyDecision:
    allowed: bool
    reason: str


class BrokerEventIdempotency:
    """Русский комментарий: защищает execution layer от повторной обработки broker event."""

    def build_event_key(
        self,
        *,
        broker_order_id: str,
        broker_status: str,
        filled_qty: float,
    ) -> str:
        return (
            f"{broker_order_id}|"
            f"{broker_status}|"
            f"{round(float(filled_qty or 0), 8)}"
        )

    def check(
        self,
        cur,
        *,
        broker_order_id: str,
        broker_status: str,
        filled_qty: float,
    ) -> BrokerEventIdempotencyDecision:
        if not broker_order_id:
            return BrokerEventIdempotencyDecision(
                allowed=False,
                reason="empty_broker_order_id",
            )

        event_key = self.build_event_key(
            broker_order_id=broker_order_id,
            broker_status=broker_status,
            filled_qty=filled_qty,
        )

        cur.execute("""
            create table if not exists broker_event_idempotency (
                event_key text primary key,
                created_at timestamptz not null default now()
            )
        """)

        cur.execute("""
            select 1
            from broker_event_idempotency
            where event_key = %s
            limit 1
        """, (event_key,))

        exists = cur.fetchone()

        if exists:
            return BrokerEventIdempotencyDecision(
                allowed=False,
                reason=f"duplicate_broker_event:{event_key}",
            )

        cur.execute("""
            insert into broker_event_idempotency (
                event_key
            )
            values (%s)
        """, (event_key,))

        return BrokerEventIdempotencyDecision(
            allowed=True,
            reason="broker_event_accepted",
        )
