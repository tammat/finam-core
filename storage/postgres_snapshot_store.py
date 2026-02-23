import psycopg2
from psycopg2.extras import Json


class PostgresSnapshotStore:
    """
    Snapshot store for event-sourced streams.

    Design goals:
    - Store only the latest snapshot per (stream, last_seq)
    - Allow fast bootstrap via ORDER BY last_seq DESC LIMIT 1
    - Keep implementation replay-safe and deterministic
    """

    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError("dsn is required for PostgresSnapshotStore")
        self.dsn = dsn

    # ------------------------------------------------
    # CONNECTION
    # ------------------------------------------------
    def _get_conn(self):
        return psycopg2.connect(self.dsn)

    # ------------------------------------------------
    # SAVE SNAPSHOT
    # ------------------------------------------------
    def save(self, stream: str, last_seq: int, state: dict) -> None:
        """
        Persist snapshot for given stream and sequence.

        We allow multiple historical snapshots but rely on
        ORDER BY last_seq DESC LIMIT 1 when loading.
        """
        if stream is None:
            raise ValueError("stream is required")

        if last_seq is None:
            raise ValueError("last_seq is required")

        if not isinstance(state, dict):
            raise ValueError("state must be dict")

        sql = """
        INSERT INTO stream_snapshots (stream, last_seq, state, created_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT DO NOTHING
        """

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (stream, last_seq, Json(state)))
            conn.commit()

    # ------------------------------------------------
    # LOAD LATEST SNAPSHOT
    # ------------------------------------------------
    def load_latest(self, stream: str):
        """
        Return latest snapshot for stream.

        Returns:
            None if no snapshot exists
            dict: {
                "last_seq": int,
                "state": dict
            }
        """
        if stream is None:
            raise ValueError("stream is required")

        sql = """
        SELECT last_seq, state
        FROM stream_snapshots
        WHERE stream = %s
        ORDER BY last_seq DESC
        LIMIT 1
        """

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (stream,))
                row = cur.fetchone()

        if not row:
            return None

        return {
            "last_seq": row[0],
            "state": row[1],
        }