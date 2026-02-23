import psycopg2
from psycopg2.extras import Json


class PostgresSnapshotStore:
    def __init__(self, dsn):
        self.dsn = dsn

    def _get_conn(self):
        return psycopg2.connect(self.dsn)

    # ------------------------------------------------
    # SAVE SNAPSHOT
    # ------------------------------------------------
    def save(self, stream: str, last_seq: int, state: dict):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stream_snapshots(stream, last_seq, state)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (stream, last_seq) DO NOTHING
                    """,
                    (stream, last_seq, Json(state)),
                )
                conn.commit()

    # ------------------------------------------------
    # LOAD LATEST SNAPSHOT
    # ------------------------------------------------
    def load_latest(self, stream: str):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT last_seq, state
                    FROM stream_snapshots
                    WHERE stream = %s
                    ORDER BY last_seq DESC
                    LIMIT 1
                    """,
                    (stream,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {"last_seq": row[0], "state": row[1]}