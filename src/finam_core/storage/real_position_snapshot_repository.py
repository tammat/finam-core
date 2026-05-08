# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import psycopg2


class RealPositionSnapshotRepository:
    """Русский комментарий: сохраняет read-only снимки реальных позиций Финама."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam user=finam password=finam host=localhost",
        )

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def save_positions(self, positions: list[dict]) -> int:
        if not positions:
            return 0

        sql = """
        INSERT INTO real_position_snapshots (
            symbol, qty, avg_price, market_price, unrealized_pnl, raw_json
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """

        rows = []
        for p in positions:
            rows.append(
                (
                    str(p.get("symbol") or ""),
                    float(p.get("qty") or 0.0),
                    self._nullable_float(p.get("avg_price")),
                    self._nullable_float(p.get("market_price")),
                    self._nullable_float(p.get("unrealized_pnl")),
                    json.dumps(p, ensure_ascii=False, default=str),
                )
            )

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, rows)

        return len(rows)

    @staticmethod
    def _nullable_float(value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except Exception:
            return None
