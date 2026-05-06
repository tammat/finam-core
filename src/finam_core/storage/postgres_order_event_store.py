# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import Json


class PostgresOrderEventStore:
    """Русский комментарий: хранилище lifecycle событий заявок."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def log_event(
        self,
        *,
        order_id: str,
        symbol: str,
        side: str,
        state: str,
        qty: float,
        filled_qty: float,
        remaining_qty: float,
        fill_price: float | None = None,
        avg_fill_price: float | None = None,
        reason: str | None = None,
        raw_json: dict | None = None,
    ) -> None:
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO order_events (
                            order_id, symbol, side, state,
                            qty, filled_qty, remaining_qty,
                            fill_price, avg_fill_price, reason, raw_json
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            order_id,
                            symbol,
                            side,
                            state,
                            float(qty),
                            float(filled_qty),
                            float(remaining_qty),
                            fill_price,
                            avg_fill_price,
                            reason,
                            Json(raw_json or {}),
                        ),
                    )
        finally:
            conn.close()
