# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


class DailyRiskRepository:
    """Русский комментарий: читает дневную equity curve из portfolio_snapshots."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam_core user=finam password=finam host=localhost",
        )

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def load_today_equities(self) -> list[float]:
        sql = """
        SELECT equity
        FROM portfolio_snapshots
        WHERE ts::date = now()::date
          AND equity IS NOT NULL
        ORDER BY ts ASC
        """

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                return [float(r["equity"]) for r in cur.fetchall()]
