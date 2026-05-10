from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras

from finam_core.events.event_store import StoredEvent
from finam_core.projections.projection_engine import ProjectionEngine
from finam_core.projections.projection_store import ProjectionStore


@dataclass(frozen=True)
class DeadLetterReplayResult:
    ok: bool
    id: int
    event_id: str | None
    reason: str


class DeadLetterReplayService:
    """Русский комментарий: повторно применяет DLQ event к projections и помечает resolved при успехе."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        engine: ProjectionEngine | None = None,
        store: ProjectionStore | None = None,
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for DeadLetterReplayService")

        # Русский комментарий: replay должен падать явно, если event всё ещё broken.
        self.engine = engine or ProjectionEngine(strict=True)
        self.store = store or ProjectionStore()

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def _load_dead_letter(self, *, dlq_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        event_db_id,
                        event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        source,
                        payload,
                        resolved
                    FROM event_dead_letters
                    WHERE id = %s
                    """,
                    (int(dlq_id),),
                )
                row = cur.fetchone()

        return dict(row) if row else None

    def _mark_resolved(self, *, dlq_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE event_dead_letters
                    SET resolved = true
                    WHERE id = %s
                    """,
                    (int(dlq_id),),
                )

    @staticmethod
    def _clean_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = dict(payload or {})
        payload.pop("_dead_letter_stacktrace", None)
        return payload

    def replay_one(self, *, dlq_id: int) -> DeadLetterReplayResult:
        row = self._load_dead_letter(dlq_id=dlq_id)

        if row is None:
            return DeadLetterReplayResult(
                ok=False,
                id=int(dlq_id),
                event_id=None,
                reason="not_found",
            )

        if bool(row["resolved"]):
            return DeadLetterReplayResult(
                ok=True,
                id=int(dlq_id),
                event_id=row.get("event_id"),
                reason="already_resolved",
            )

        event = StoredEvent(
            db_id=row.get("event_db_id"),
            event_id=row.get("event_id") or "",
            event_type=row.get("event_type") or "",
            aggregate_type=row.get("aggregate_type") or "system",
            aggregate_id=row.get("aggregate_id"),
            source=row.get("source") or "dlq",
            payload=self._clean_payload(row.get("payload")),
        )

        state = self.engine.empty_state()
        self.engine.apply_event(state, event)
        self.store.save(state)

        self._mark_resolved(dlq_id=dlq_id)

        return DeadLetterReplayResult(
            ok=True,
            id=int(dlq_id),
            event_id=event.event_id,
            reason="replayed_and_resolved",
        )
