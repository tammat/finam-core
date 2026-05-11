# -*- coding: utf-8 -*-
"""
ProtectiveOrderLinkRepository — хранение связок entry ↔ stop/take в PostgreSQL.
"""

from __future__ import annotations

import json
import os

import psycopg2

from finam_core.execution.protective_order_link import ProtectiveOrderLink


class ProtectiveOrderLinkRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
        self.enabled = os.getenv("PROTECTIVE_ORDER_LINKS_ENABLED", "1") == "1"

    def save(self, link: ProtectiveOrderLink) -> int | None:
        """Русский комментарий: запись связки не должна ломать trading pipeline."""
        if not self.enabled or not self.database_url:
            return None

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO protective_order_links
                            (symbol, side, qty, entry_order_id, stop_order_id, take_order_id, status, source, raw)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        RETURNING id
                        """,
                        (
                            link.symbol,
                            link.side,
                            float(link.qty),
                            link.entry_order_id,
                            link.stop_order_id,
                            link.take_order_id,
                            link.status,
                            link.source,
                            json.dumps(link.raw or {}, ensure_ascii=False, default=str),
                        ),
                    )
                    return int(cur.fetchone()[0])
        except Exception as exc:
            print(f"PROTECTIVE_ORDER_LINK_SAVE_FAILED error={exc}", flush=True)
            return None

    def list_open_unprotected(self, *, limit: int = 100) -> list[ProtectiveOrderLink]:
        """Русский комментарий: ищем открытые entry без stop/take для Grafana/recovery."""
        if not self.enabled or not self.database_url:
            return []

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT symbol, side, qty, entry_order_id, stop_order_id, take_order_id, status, source, raw
                    FROM protective_order_links
                    WHERE status = 'OPEN'
                      AND (stop_order_id IS NULL OR stop_order_id = '')
                      AND (take_order_id IS NULL OR take_order_id = '')
                    ORDER BY ts DESC
                    LIMIT %s
                    """,
                    (int(limit),),
                )
                rows = cur.fetchall()

        return [
            ProtectiveOrderLink(
                symbol=str(symbol),
                side=str(side),
                qty=float(qty or 0.0),
                entry_order_id=str(entry_order_id),
                stop_order_id=str(stop_order_id) if stop_order_id else None,
                take_order_id=str(take_order_id) if take_order_id else None,
                status=str(status),
                source=str(source),
                raw=raw if isinstance(raw, dict) else {},
            )
            for symbol, side, qty, entry_order_id, stop_order_id, take_order_id, status, source, raw in rows
        ]
