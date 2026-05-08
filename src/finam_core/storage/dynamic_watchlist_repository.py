# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import psycopg2


class DynamicWatchlistRepository:
    """
    Русский комментарий:
    Хранит TOP кандидатов для realtime monitoring.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv(
            "DATABASE_URL",
            "dbname=finam user=finam password=finam host=localhost",
        )

    def replace_watchlist(self, rows: list[dict]) -> int:
        if not rows:
            return 0

        sql_delete = "DELETE FROM dynamic_watchlist"

        sql_insert = """
        INSERT INTO dynamic_watchlist (
            symbol,
            name,
            direction,
            score,
            relative_strength,
            portfolio_status,
            portfolio_action,
            appearances,
            score_delta,
            persistence_state,
            source
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'market_radar')
        """

        payload = [
            (
                r.get("symbol"),
                r.get("name"),
                r.get("direction"),
                r.get("score"),
                r.get("relative_strength"),
                r.get("portfolio_status"),
                r.get("portfolio_action"),
                r.get("appearances", 0),
                r.get("score_delta", 0.0),
                r.get("persistence_state", "UNKNOWN"),
            )
            for r in rows
        ]

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_delete)
                cur.executemany(sql_insert, payload)

        return len(payload)

    def load_watchlist(self) -> list[dict]:
        sql = """
        SELECT
            symbol,
            name,
            direction,
            score,
            relative_strength,
            portfolio_status,
            portfolio_action,
            ts
        FROM dynamic_watchlist
        ORDER BY score DESC
        """

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

                rows = []

                for r in cur.fetchall():
                    rows.append(
                        {
                            "symbol": r[0],
                            "name": r[1],
                            "direction": r[2],
                            "score": float(r[3] or 0.0),
                            "relative_strength": float(r[4] or 0.0),
                            "portfolio_status": r[5],
                            "portfolio_action": r[6],
                            "ts": r[7],
                        }
                    )

                return rows
