import uuid
import json
from typing import Callable, Any, Dict, Iterable, Optional
import psycopg2
from psycopg2.extras import Json


class PostgresEventStore:
    """
    Production-grade append-only event store.

    Guarantees:
    - Strict ordering via BIGSERIAL seq
    - Idempotency via UUID
    - Stream isolation
    - Deterministic replay (ORDER BY seq)
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._ensure_table()

    def _get_conn(self):
        return psycopg2.connect(self.dsn)

    def _ensure_table(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        seq BIGSERIAL PRIMARY KEY,
                        id UUID NOT NULL UNIQUE,
                        stream VARCHAR(128) NOT NULL,
                        event_type VARCHAR(128) NOT NULL,
                        version INTEGER NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        payload JSONB NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_stream_seq
                    ON events(stream, seq);
                    """
                )
            conn.commit()

    # ------------------------------------------------------------
    # Append
    # ------------------------------------------------------------

    def append(
        self,
        stream: str,
        event_type: str,
        payload: Dict[str, Any],
        version: int = 1,
        event_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Appends event and returns stored metadata.
        """

        if event_id is None:
            event_id = uuid.uuid4()

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO events (id, stream, event_type, version, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING seq, created_at
                    """,
                    (
                        str(event_id),
                        stream,
                        event_type,
                        version,
                        Json(payload),
                    ),
                )
                seq, created_at = cur.fetchone()
            conn.commit()

        return {
            "seq": seq,
            "id": event_id,
            "stream": stream,
            "event_type": event_type,
            "version": version,
            "created_at": created_at,
        }

    # ------------------------------------------------------------
    # Load
    # ------------------------------------------------------------

    def load_stream(self, stream: str) -> Iterable[Dict[str, Any]]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT seq, id, event_type, version, payload
                    FROM events
                    WHERE stream = %s
                    ORDER BY seq ASC
                    """,
                    (stream,),
                )
                rows = cur.fetchall()

        for seq, event_id, event_type, version, payload in rows:
            yield {
                "seq": seq,
                "id": event_id,
                "event_type": event_type,
                "version": version,
                "payload": payload,
            }

    # ------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------

    def replay_stream(
        self,
        stream: str,
        handler: Callable[[Dict[str, Any]], None],
    ):
        for event in self.load_stream(stream):
            handler(event)


    def replay_from(self, stream: str, from_seq: int, handler):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT seq, event_type, payload
                    FROM events
                    WHERE stream = %s
                      AND seq > %s
                    ORDER BY seq ASC
                    """,
                    (stream, from_seq),
                )
                for seq, event_type, payload in cur.fetchall():
                    handler({
                        "seq": seq,
                        "event_type": event_type,
                        "payload": payload,
                    })