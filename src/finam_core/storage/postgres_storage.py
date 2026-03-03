import os
import logging
from finam_core.storage.base_storage import BaseStorage

from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool


class PostgresStorage:

    def __init__(
        self,
        dsn: str = None,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        database: str = None,
        min_conn: int = 1,
        max_conn: int = 5,
    ):

        if dsn:
            self._pool = pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                dsn=dsn,
            )
        else:
            assert host and username and password and database, \
                "Either DSN or full DB credentials required"

            self._pool = pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                host=host,
                port=port,
                user=username,
                password=password,
                dbname=database,
            )

        if not self._pool:
            raise RuntimeError("Failed to initialize Postgres pool")

        logger.info("Postgres pool initialized")

    # ---------- connection management ----------

    @contextmanager
    def connection(self):
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def cursor(self) -> Generator:
        with self.connection() as conn:
            with conn.cursor() as cur:
                yield cur

    # ---------- health ----------

    def health_check(self) -> bool:
        try:
            with self.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("DB health check failed: %s", e)
            return False

    # ---------- shutdown ----------

    def close(self):
        if self._pool:
            self._pool.closeall()
            logger.info("Postgres pool closed")