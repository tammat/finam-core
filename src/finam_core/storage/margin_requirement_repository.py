# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os

import psycopg2
from psycopg2.extras import RealDictCursor


class MarginRequirementRepository:
    """Русский комментарий: PostgreSQL-хранилище требований ГО/маржи."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam_core user=finam password=finam host=localhost",
        )

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def upsert_requirement(self, row: dict) -> None:
        sql = """
        INSERT INTO margin_requirements (
            symbol, base_symbol, asset_class,
            initial_margin, maintenance_margin,
            currency, source, active, updated_at, raw_json
        )
        VALUES (
            %(symbol)s, %(base_symbol)s, %(asset_class)s,
            %(initial_margin)s, %(maintenance_margin)s,
            %(currency)s, %(source)s, %(active)s, now(), %(raw_json)s::jsonb
        )
        ON CONFLICT (symbol) DO UPDATE SET
            base_symbol = EXCLUDED.base_symbol,
            asset_class = EXCLUDED.asset_class,
            initial_margin = EXCLUDED.initial_margin,
            maintenance_margin = EXCLUDED.maintenance_margin,
            currency = EXCLUDED.currency,
            source = EXCLUDED.source,
            active = EXCLUDED.active,
            updated_at = now(),
            raw_json = EXCLUDED.raw_json
        """

        payload = dict(row)
        payload["symbol"] = str(payload["symbol"]).upper()
        payload["base_symbol"] = str(payload.get("base_symbol") or payload["symbol"].split("@", 1)[0]).upper()
        payload["asset_class"] = str(payload.get("asset_class") or "FUTURES").upper()
        payload.setdefault("initial_margin", 0.0)
        payload.setdefault("maintenance_margin", payload["initial_margin"])
        payload.setdefault("currency", "RUB")
        payload.setdefault("source", "manual")
        payload.setdefault("active", True)
        payload["raw_json"] = json.dumps(payload.get("raw_json") or row, ensure_ascii=False, default=str)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, payload)

    def get_by_symbol(self, symbol: str) -> dict | None:
        symbol_u = str(symbol or "").upper()
        base = symbol_u.split("@", 1)[0]

        sql = """
        SELECT *
        FROM margin_requirements
        WHERE active = TRUE
          AND (symbol = %s OR base_symbol = %s)
        ORDER BY
          CASE WHEN symbol = %s THEN 0 ELSE 1 END,
          updated_at DESC
        LIMIT 1
        """

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (symbol_u, base, symbol_u))
                row = cur.fetchone()
                return dict(row) if row else None
