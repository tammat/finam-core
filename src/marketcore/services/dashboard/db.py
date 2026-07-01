from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


@contextmanager
def db_cursor() -> Iterator[object]:
    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    finally:
        conn.close()


def table_exists(cur: object, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None
