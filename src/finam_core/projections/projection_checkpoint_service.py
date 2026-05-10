from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class ProjectionCheckpoint:
    name: str
    last_event_id: int


class ProjectionCheckpointService:
    """Русский комментарий: хранит offset последнего обработанного event_store.id для projections."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for ProjectionCheckpointService")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        with open("sql/20260510_projection_checkpoints.sql", "r", encoding="utf-8") as f:
            sql = f.read()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def get(self, *, name: str = "default") -> ProjectionCheckpoint:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT name, last_event_id
                    FROM projection_checkpoints
                    WHERE name = %s
                    """,
                    (name,),
                )
                row = cur.fetchone()

        if not row:
            return ProjectionCheckpoint(name=name, last_event_id=0)

        return ProjectionCheckpoint(
            name=str(row["name"]),
            last_event_id=int(row["last_event_id"]),
        )

    def update(self, *, name: str = "default", last_event_id: int) -> ProjectionCheckpoint:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO projection_checkpoints (name, last_event_id, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (name)
                    DO UPDATE SET
                        last_event_id = GREATEST(
                            projection_checkpoints.last_event_id,
                            EXCLUDED.last_event_id
                        ),
                        updated_at = now()
                    RETURNING name, last_event_id
                    """,
                    (name, int(last_event_id)),
                )
                row = cur.fetchone()

        return ProjectionCheckpoint(
            name=str(row["name"]),
            last_event_id=int(row["last_event_id"]),
        )
