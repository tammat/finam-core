# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor


class FeeProfileRepository:
    """Русский комментарий: хранит тарифы брокера/биржи/клиринга."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam_core user=finam password=finam host=localhost",
        )

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def upsert_profile(self, profile: dict) -> None:
        sql = """
        INSERT INTO fee_profiles (
            profile_name, asset_class, symbol_prefix,
            broker_fee_per_contract, exchange_fee_per_contract, clearing_fee_per_contract,
            broker_fee_pct, exchange_fee_pct, min_fee,
            currency, source, active, updated_at, raw_json
        )
        VALUES (
            %(profile_name)s, %(asset_class)s, %(symbol_prefix)s,
            %(broker_fee_per_contract)s, %(exchange_fee_per_contract)s, %(clearing_fee_per_contract)s,
            %(broker_fee_pct)s, %(exchange_fee_pct)s, %(min_fee)s,
            %(currency)s, %(source)s, %(active)s, now(), %(raw_json)s::jsonb
        )
        """

        payload = dict(profile)
        payload.setdefault("symbol_prefix", None)
        payload.setdefault("broker_fee_per_contract", 0.0)
        payload.setdefault("exchange_fee_per_contract", 0.0)
        payload.setdefault("clearing_fee_per_contract", 0.0)
        payload.setdefault("broker_fee_pct", 0.0)
        payload.setdefault("exchange_fee_pct", 0.0)
        payload.setdefault("min_fee", 0.0)
        payload.setdefault("currency", "RUB")
        payload.setdefault("source", "manual")
        payload.setdefault("active", True)
        payload["raw_json"] = json.dumps(payload.get("raw_json") or profile, ensure_ascii=False)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, payload)

    def get_profile(self, *, asset_class: str, symbol: str) -> dict | None:
        base = str(symbol or "").upper().split("@", 1)[0]
        sql = """
        SELECT *
        FROM fee_profiles
        WHERE active = TRUE
          AND asset_class = %s
          AND (symbol_prefix IS NULL OR %s LIKE symbol_prefix || '%%')
        ORDER BY
          CASE WHEN symbol_prefix IS NULL THEN 1 ELSE 0 END,
          length(symbol_prefix) DESC NULLS LAST,
          updated_at DESC
        LIMIT 1
        """

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (asset_class.upper(), base))
                row = cur.fetchone()
                return dict(row) if row else None
