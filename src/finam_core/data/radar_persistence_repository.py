# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import psycopg2

from finam_core.data.radar_persistence_engine import RadarPersistenceEngine


class RadarPersistenceRepository:
    """Русский комментарий: считает устойчивость кандидатов по market_radar_results."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv(
            "DATABASE_URL",
            "dbname=finam user=finam password=finam host=localhost",
        )
        self.engine = RadarPersistenceEngine()

    def load_persistence(self, hours: int = 4) -> dict[str, dict]:
        sql = """
        SELECT symbol, ts, score, relative_strength
        FROM market_radar_results
        WHERE ts >= NOW() - (%s || ' hours')::interval
          AND status = 'CANDIDATE'
        ORDER BY symbol, ts
        """

        grouped: dict[str, list[dict]] = {}

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (hours,))
                for symbol, ts, score, rs in cur.fetchall():
                    grouped.setdefault(symbol, []).append(
                        {
                            "symbol": symbol,
                            "ts": ts,
                            "score": float(score or 0.0),
                            "relative_strength": float(rs or 0.0),
                        }
                    )

        result: dict[str, dict] = {}

        for symbol, rows in grouped.items():
            classified = self.engine.classify(rows)
            if classified is None:
                continue

            result[symbol] = {
                "appearances": classified.appearances,
                "avg_score": classified.avg_score,
                "last_score": classified.last_score,
                "score_delta": classified.score_delta,
                "avg_relative_strength": classified.avg_relative_strength,
                "last_relative_strength": classified.last_relative_strength,
                "persistence_state": classified.state,
            }

        return result
