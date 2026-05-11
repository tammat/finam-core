# -*- coding: utf-8 -*-
"""
OrderAckRepository — чтение ACK из PostgreSQL для reconciliation.
"""

from __future__ import annotations

import os
import psycopg2

from finam_core.execution.order_ack import OrderAck


class OrderAckRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()

    def list_recent(self, *, limit: int = 100) -> list[OrderAck]:
        if not self.database_url:
            return []

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT symbol, side, qty, order_id, status, reason, raw
                    FROM order_acks
                    ORDER BY ts DESC
                    LIMIT %s
                    """,
                    (int(limit),),
                )
                rows = cur.fetchall()

        result: list[OrderAck] = []
        for symbol, side, qty, order_id, status, reason, raw in rows:
            result.append(
                OrderAck(
                    accepted=bool(order_id) and str(reason or "") == "",
                    symbol=str(symbol),
                    side=str(side),
                    qty=float(qty or 0.0),
                    order_id=str(order_id) if order_id else None,
                    status=str(status),
                    reason=str(reason) if reason else None,
                    raw=raw if isinstance(raw, dict) else {},
                )
            )
        return result
