# -*- coding: utf-8 -*-
"""
OrderAckLogger — запись ACK брокера после PlaceOrder в PostgreSQL.
"""

from __future__ import annotations

import json
import os
import psycopg2

from finam_core.execution.order_ack import OrderAck


class OrderAckLogger:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
        self.enabled = os.getenv("ORDER_ACK_LOGGER_ENABLED", "1") == "1"

    def log(self, ack: OrderAck, *, source: str = "finam_orders_client") -> None:
        """Русский комментарий: логирование ACK не должно ломать торговый pipeline."""
        if not self.enabled or not self.database_url:
            return

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO order_acks
                            (symbol, side, qty, order_id, status, reason, source, raw)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            ack.symbol,
                            ack.side,
                            float(ack.qty),
                            ack.order_id,
                            ack.status,
                            ack.reason,
                            source,
                            json.dumps(ack.raw or {}, ensure_ascii=False, default=str),
                        ),
                    )
        except Exception as exc:
            print(f"ORDER_ACK_LOG_FAILED error={exc}", flush=True)
