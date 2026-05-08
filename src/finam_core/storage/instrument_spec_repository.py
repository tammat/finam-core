# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor


class InstrumentSpecRepository:
    """Русский комментарий: PostgreSQL-хранилище спецификаций инструментов."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam user=finam password=finam host=localhost",
        )

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def upsert_spec(self, spec: dict) -> None:
        sql = """
        INSERT INTO instrument_specs (
            symbol, base_symbol, asset_class, exchange, board,
            min_price_step, step_value, lot_size, currency,
            initial_margin, maintenance_margin,
            broker_fee, exchange_fee, clearing_fee, tax_rate,
            source, updated_at, raw_json
        )
        VALUES (
            %(symbol)s, %(base_symbol)s, %(asset_class)s, %(exchange)s, %(board)s,
            %(min_price_step)s, %(step_value)s, %(lot_size)s, %(currency)s,
            %(initial_margin)s, %(maintenance_margin)s,
            %(broker_fee)s, %(exchange_fee)s, %(clearing_fee)s, %(tax_rate)s,
            %(source)s, now(), %(raw_json)s::jsonb
        )
        ON CONFLICT (symbol) DO UPDATE SET
            base_symbol = EXCLUDED.base_symbol,
            asset_class = EXCLUDED.asset_class,
            exchange = EXCLUDED.exchange,
            board = EXCLUDED.board,
            min_price_step = EXCLUDED.min_price_step,
            step_value = EXCLUDED.step_value,
            lot_size = EXCLUDED.lot_size,
            currency = EXCLUDED.currency,
            initial_margin = EXCLUDED.initial_margin,
            maintenance_margin = EXCLUDED.maintenance_margin,
            broker_fee = EXCLUDED.broker_fee,
            exchange_fee = EXCLUDED.exchange_fee,
            clearing_fee = EXCLUDED.clearing_fee,
            tax_rate = EXCLUDED.tax_rate,
            source = EXCLUDED.source,
            updated_at = now(),
            raw_json = EXCLUDED.raw_json
        """

        payload = dict(spec)
        payload.setdefault("exchange", None)
        payload.setdefault("board", None)
        payload.setdefault("lot_size", 1.0)
        payload.setdefault("currency", "RUB")
        payload.setdefault("initial_margin", None)
        payload.setdefault("maintenance_margin", None)
        payload.setdefault("broker_fee", 0.0)
        payload.setdefault("exchange_fee", 0.0)
        payload.setdefault("clearing_fee", 0.0)
        payload.setdefault("tax_rate", 0.13)
        payload.setdefault("source", "manual")
        payload["raw_json"] = json.dumps(payload.get("raw_json") or spec, ensure_ascii=False, default=str)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, payload)

    def get_by_symbol(self, symbol: str) -> dict | None:
        sql = """
        SELECT *
        FROM instrument_specs
        WHERE symbol = %s OR base_symbol = %s
        ORDER BY
            CASE WHEN symbol = %s THEN 0 ELSE 1 END,
            updated_at DESC
        LIMIT 1
        """

        base = str(symbol or "").upper().split("@", 1)[0]

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (str(symbol).upper(), base, str(symbol).upper()))
                row = cur.fetchone()
                return dict(row) if row else None

    def list_specs(self) -> list[dict]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM instrument_specs ORDER BY asset_class, symbol")
                return [dict(r) for r in cur.fetchall()]
