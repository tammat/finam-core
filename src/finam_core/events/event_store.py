from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class StoredEvent:
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str | None
    source: str
    payload: dict[str, Any]


class EventStore:
    """Русский комментарий: append-only PostgreSQL event store для audit/replay/recovery."""

    def __init__(self, database_url: str | None = None, event_bus: Any | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        # Русский комментарий: event_bus опционален, чтобы EventStore оставался совместимым со старым кодом.
        self.event_bus = event_bus
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for EventStore")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        with open("sql/20260510_event_store.sql", "r", encoding="utf-8") as f:
            sql = f.read()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def _publish_event_safe(self, event: StoredEvent) -> None:
        """Русский комментарий: публикация StoredEvent в EventBus не должна ломать append."""
        if self.event_bus is None:
            return

        try:
            if hasattr(self.event_bus, "publish"):
                try:
                    self.event_bus.publish("EVENT_STORE_APPENDED", event)
                except TypeError:
                    self.event_bus.publish(event)
        except Exception as exc:
            print(
                f"EVENT_STORE_BUS_PUBLISH_FAILED event_id={event.event_id} error={exc}",
                flush=True,
            )


    @staticmethod
    def build_event_id(
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str | None,
        payload: dict[str, Any],
    ) -> str:
        """Русский комментарий: deterministic id для защиты от дублей при retry."""
        body = json.dumps(
            {
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "payload": payload,
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]
        return f"evt_{digest}"

    def append(
        self,
        *,
        event_type: str,
        aggregate_type: str = "system",
        aggregate_id: str | None = None,
        source: str = "system",
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
    ) -> tuple[bool, StoredEvent]:
        """Русский комментарий: append-only insert; duplicate event_id возвращает существующее событие."""
        self.ensure_schema()

        payload = payload or {}
        event_id = event_id or self.build_event_id(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO event_store (
                        event_id, event_type, aggregate_type, aggregate_id, source, payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    RETURNING event_id, event_type, aggregate_type, aggregate_id, source, payload
                    """,
                    (
                        event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        source,
                        psycopg2.extras.Json(payload),
                    ),
                )
                row = cur.fetchone()

                if row:
                    event = StoredEvent(**dict(row))
                    self._publish_event_safe(event)
                    return True, event

                cur.execute(
                    """
                    SELECT event_id, event_type, aggregate_type, aggregate_id, source, payload
                    FROM event_store
                    WHERE event_id = %s
                    """,
                    (event_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    raise RuntimeError(f"EventStore duplicate not found: {event_id}")

                return False, StoredEvent(**dict(existing))

    def list_by_aggregate(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        limit: int = 100,
    ) -> list[StoredEvent]:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT event_id, event_type, aggregate_type, aggregate_id, source, payload
                    FROM event_store
                    WHERE aggregate_type = %s AND aggregate_id = %s
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (aggregate_type, aggregate_id, int(limit)),
                )
                rows = cur.fetchall()

        return [StoredEvent(**dict(row)) for row in rows]
