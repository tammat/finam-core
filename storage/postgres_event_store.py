from __future__ import annotations

import json
from typing import Callable, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


class PostgresEventStore:
    """
    Production-ready event store with:
      - optimistic concurrency
      - append-first consistency
      - stream replay
    """

    def __init__(self, dsn: str):
        self._dsn = dsn

    # =========================================================
    # Connection
    # =========================================================

    def _get_conn(self):
        return psycopg2.connect(self._dsn)

    # =========================================================
    # Versioning
    # =========================================================

    def get_stream_version(self, stream: str) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM events WHERE stream = %s",
                    (stream,),
                )
                return cur.fetchone()[0]

    # =========================================================
    # Append (exactly-once + optimistic concurrency)
    # =========================================================

    def append(
            self,
            *,
            stream: str,
            event_id,
            event_type: str,
            payload: dict,
            expected_version: int,
    ):
        import json
        import psycopg2

        with self._get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COALESCE(MAX(version), 0) FROM events WHERE stream = %s",
                        (stream,),
                    )
                    current_version = cur.fetchone()[0]

                    if current_version != expected_version:
                        raise RuntimeError(
                            f"Concurrency conflict: expected {expected_version}, got {current_version}"
                        )

                    version = expected_version + 1

                    cur.execute(
                        """
                        INSERT INTO events (id, stream, event_type, version, payload)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            str(event_id),
                            stream,
                            event_type,
                            version,
                            json.dumps(payload, default=str),  # UUID в payload -> str
                        ),
                    )

                conn.commit()

            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                return    # =========================================================
    # Replay
    # =========================================================

    def replay_stream(
        self,
        stream: str,
        handler: Callable[[dict], None],
        from_version: Optional[int] = None,
    ):
        """
        Replay events for a given stream in order.
        """

        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                if from_version is not None:
                    cur.execute(
                        """
                        SELECT * FROM events
                        WHERE stream = %s AND version > %s
                        ORDER BY version ASC
                        """,
                        (stream, from_version),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM events
                        WHERE stream = %s
                        ORDER BY version ASC
                        """,
                        (stream,),
                    )

                rows = cur.fetchall()

                for row in rows:
                    event_dict = {
                        "id": row["id"],
                        "stream": row["stream"],
                        "event_type": row["event_type"],
                        "version": row["version"],
                        "payload": row["payload"],
                    }
                    handler(event_dict)