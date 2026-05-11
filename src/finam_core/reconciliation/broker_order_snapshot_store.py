# -*- coding: utf-8 -*-
"""
BrokerOrderSnapshotStore — сохранение снимков broker orders из GetOrders.

Русский комментарий: нужен для истории состояния заявок и последующей сверки ACK ↔ broker state.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict

import psycopg2

from finam_core.reconciliation.broker_order_reconciliation import BrokerOrderState


class BrokerOrderSnapshotStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
        self.enabled = os.getenv("BROKER_ORDER_SNAPSHOT_STORE_ENABLED", "1") == "1"

    def save_many(
        self,
        orders: list[BrokerOrderState],
        *,
        source: str = "finam_get_orders",
    ) -> int:
        """Русский комментарий: сохранение снимков не должно ломать reconciliation timer."""
        if not self.enabled or not self.database_url or not orders:
            return 0

        saved = 0
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    for order in orders:
                        remaining_qty = max(float(order.qty or 0.0) - float(order.filled_qty or 0.0), 0.0)
                        cur.execute(
                            """
                            INSERT INTO broker_order_snapshots
                                (order_id, symbol, side, status, qty, filled_qty, remaining_qty, source, raw)
                            VALUES
                                (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                            """,
                            (
                                order.order_id,
                                order.symbol,
                                order.side,
                                order.status,
                                float(order.qty or 0.0),
                                float(order.filled_qty or 0.0),
                                remaining_qty,
                                source,
                                json.dumps(asdict(order), ensure_ascii=False, default=str),
                            ),
                        )
                        saved += 1
            return saved
        except Exception as exc:
            print(f"BROKER_ORDER_SNAPSHOT_STORE_FAILED error={exc}", flush=True)
            return saved
