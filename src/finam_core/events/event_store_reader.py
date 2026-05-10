from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator

import psycopg2
import psycopg2.extras

from finam_core.events.event_store import StoredEvent


@dataclass(frozen=True)
class ReplayAggregateResult:
    aggregate_type: str
    aggregate_id: str
    events: list[StoredEvent]


class EventStoreReader:
    """Русский комментарий: replay/read API для append-only event store."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def list_by_type(
        self,
        *,
        event_type: str,
        limit: int = 100,
    ) -> list[StoredEvent]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id AS db_id,
                        id AS db_id,
                        event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        source,
                        payload
                    FROM event_store
                    WHERE event_type = %s
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (event_type, int(limit)),
                )

                rows = cur.fetchall()

        return [StoredEvent(**dict(row)) for row in rows]

    def list_since_id(
        self,
        *,
        since_id: int,
        limit: int = 100,
    ) -> list[StoredEvent]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id AS db_id,
                        id AS db_id,
                        event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        source,
                        payload
                    FROM event_store
                    WHERE id > %s
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (int(since_id), int(limit)),
                )

                rows = cur.fetchall()

        return [StoredEvent(**dict(row)) for row in rows]

    def replay_aggregate(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        limit: int = 1000,
    ) -> ReplayAggregateResult:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id AS db_id,
                        id AS db_id,
                        event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        source,
                        payload
                    FROM event_store
                    WHERE aggregate_type = %s
                      AND aggregate_id = %s
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (
                        aggregate_type,
                        aggregate_id,
                        int(limit),
                    ),
                )

                rows = cur.fetchall()

        return ReplayAggregateResult(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            events=[StoredEvent(**dict(row)) for row in rows],
        )

    def iter_all(
        self,
        *,
        batch_size: int = 1000,
    ) -> Iterator[StoredEvent]:
        """Русский комментарий: streaming replay iterator."""
        offset = 0

        while True:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            id AS db_id,
                            id AS db_id,
                            event_id,
                            event_type,
                            aggregate_type,
                            aggregate_id,
                            source,
                            payload
                        FROM event_store
                        ORDER BY id ASC
                        LIMIT %s OFFSET %s
                        """,
                        (
                            int(batch_size),
                            int(offset),
                        ),
                    )

                    rows = cur.fetchall()

            if not rows:
                break

            for row in rows:
                yield StoredEvent(**dict(row))

            offset += len(rows)
