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

    def mark_manual_protection_required(
        self,
        *,
        entry_order_id: str,
        reason: str,
    ) -> int | None:
        """Русский комментарий: фиксирует, что автоматическая защитная заявка отклонена брокером."""
        if not self.enabled or not self.database_url or not entry_order_id:
            return None

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE protective_order_links
                        SET raw = COALESCE(raw, '{}'::jsonb) || %s::jsonb
                        WHERE entry_order_id = %s
                        RETURNING id
                        """,
                        (
                            json.dumps(
                                {
                                    "manual_protection_required": True,
                                    "protective_stop_rejected_reason": reason,
                                },
                                ensure_ascii=False,
                            ),
                            entry_order_id,
                        ),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else None
        except Exception as exc:
            print(f"PROTECTIVE_MANUAL_REQUIRED_MARK_FAILED error={exc}", flush=True)
            return None

    def has_existing_protective_order(
        self,
        *,
        entry_order_id: str,
        protective_type: str,
    ) -> bool:
        """Русский комментарий: duplicate-prevention для stop/take по entry_order_id."""
        if not self.enabled or not self.database_url or not entry_order_id:
            return False

        field_name = "stop_order_id" if protective_type == "stop" else "take_order_id" if protective_type == "take" else ""
        if not field_name:
            return False

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT 1
                        FROM protective_order_links
                        WHERE entry_order_id = %s
                          AND COALESCE({field_name}, '') <> ''
                        LIMIT 1
                        """,
                        (entry_order_id,),
                    )
                    return cur.fetchone() is not None
        except Exception as exc:
            print(f"PROTECTIVE_ORDER_DUPLICATE_CHECK_FAILED error={exc}", flush=True)
            return False

    def attach_protective_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        order_id: str,
        protective_type: str,
    ) -> int | None:
        """Русский комментарий: привязывает stop/take ACK к последней открытой entry-связке."""
        if not self.enabled or not self.database_url or not order_id:
            return None

        field_name = "stop_order_id" if protective_type == "stop" else "take_order_id" if protective_type == "take" else ""
        if not field_name:
            return None

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        UPDATE protective_order_links
                        SET {field_name} = %s,
                            raw = COALESCE(raw, '{{}}'::jsonb) || %s::jsonb
                        WHERE id = (
                            SELECT id
                            FROM protective_order_links
                            WHERE symbol = %s
                              AND side = %s
                              AND status = 'OPEN'
                            ORDER BY ts DESC
                            LIMIT 1
                        )
                        RETURNING id
                        """,
                        (
                            order_id,
                            json.dumps(
                                {
                                    "attached_protective_type": protective_type,
                                    "attached_order_id": order_id,
                                    "attached_qty": float(qty or 0.0),
                                },
                                ensure_ascii=False,
                            ),
                            symbol,
                            side,
                        ),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else None
        except Exception as exc:
            print(f"PROTECTIVE_ORDER_LINK_ATTACH_FAILED error={exc}", flush=True)
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
