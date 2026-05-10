from __future__ import annotations

import os
import traceback
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras

from finam_core.events.event_store import StoredEvent


@dataclass(frozen=True)
class DeadLetterRecord:
    id: int
    event_id: str | None
    event_type: str | None
    error_type: str
    error_message: str
    worker_name: str


class DeadLetterService:
    """Русский комментарий: DLQ для событий, которые не удалось обработать."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for DeadLetterService")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        with open("sql/20260510_event_dead_letters.sql", "r", encoding="utf-8") as f:
            sql = f.read()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def record_event_failure(
        self,
        *,
        event: StoredEvent,
        error: Exception,
        worker_name: str,
    ) -> DeadLetterRecord:
        """Русский комментарий: сохраняет failed event в DLQ и не выбрасывает исходную ошибку выше."""
        self.ensure_schema()

        error_type = type(error).__name__
        error_message = str(error)
        stack = traceback.format_exception(type(error), error, error.__traceback__)

        payload: dict[str, Any] = dict(event.payload or {})
        payload["_dead_letter_stacktrace"] = "".join(stack)

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO event_dead_letters (
                        event_db_id,
                        event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        source,
                        payload,
                        error_type,
                        error_message,
                        worker_name,
                        resolved
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false)
                    RETURNING id, event_id, event_type, error_type, error_message, worker_name
                    """,
                    (
                        event.db_id,
                        event.event_id,
                        event.event_type,
                        event.aggregate_type,
                        event.aggregate_id,
                        event.source,
                        psycopg2.extras.Json(payload),
                        error_type,
                        error_message,
                        worker_name,
                    ),
                )
                row = cur.fetchone()

        record = DeadLetterRecord(**dict(row))
        print(
            f"DLQ_EVENT_RECORDED id={record.id} event_id={record.event_id} "
            f"event_type={record.event_type} worker={record.worker_name} "
            f"error_type={record.error_type}",
            flush=True,
        )
        return record

    def unresolved_count(self) -> int:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM event_dead_letters WHERE resolved = false")
                return int(cur.fetchone()[0])
