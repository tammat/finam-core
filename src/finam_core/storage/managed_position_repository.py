from __future__ import annotations

import json
import os

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.execution.position_registry import ManagedPosition


class ManagedPositionRepository:
    def __init__(self, dsn: str | None = None):
        self.dsn = (
            dsn
            or os.getenv("FINAM_DSN")
            or os.getenv("POSTGRES_DSN")
            or "dbname=finam_core user=finam password=finam host=localhost port=5432"
        )

    def _connect(self):
        return psycopg2.connect(self.dsn)

    def ensure_schema(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS managed_positions (
            symbol TEXT PRIMARY KEY,
            side TEXT NOT NULL,
            qty DOUBLE PRECISION NOT NULL,
            entry_price DOUBLE PRECISION NOT NULL,

            stop_order_id TEXT,
            tp1_order_id TEXT,
            tp2_order_id TEXT,

            breakeven_done BOOLEAN NOT NULL DEFAULT FALSE,
            tp1_done BOOLEAN NOT NULL DEFAULT FALSE,
            tp2_done BOOLEAN NOT NULL DEFAULT FALSE,

            payload JSONB NOT NULL DEFAULT '{}'::jsonb,

            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save(self, pos: ManagedPosition) -> None:
        sql = """
        INSERT INTO managed_positions (
            symbol,
            side,
            qty,
            entry_price,
            stop_order_id,
            tp1_order_id,
            tp2_order_id,
            breakeven_done,
            tp1_done,
            tp2_done,
            payload,
            updated_at
        )
        VALUES (
            %(symbol)s,
            %(side)s,
            %(qty)s,
            %(entry_price)s,
            %(stop_order_id)s,
            %(tp1_order_id)s,
            %(tp2_order_id)s,
            %(breakeven_done)s,
            %(tp1_done)s,
            %(tp2_done)s,
            %(payload)s::jsonb,
            now()
        )
        ON CONFLICT (symbol)
        DO UPDATE SET
            side = EXCLUDED.side,
            qty = EXCLUDED.qty,
            entry_price = EXCLUDED.entry_price,
            stop_order_id = EXCLUDED.stop_order_id,
            tp1_order_id = EXCLUDED.tp1_order_id,
            tp2_order_id = EXCLUDED.tp2_order_id,
            breakeven_done = EXCLUDED.breakeven_done,
            tp1_done = EXCLUDED.tp1_done,
            tp2_done = EXCLUDED.tp2_done,
            payload = EXCLUDED.payload,
            updated_at = now();
        """

        payload = {
            "symbol": pos.symbol,
            "side": pos.side,
            "qty": pos.qty,
            "entry_price": pos.entry_price,
        }

        params = {
            "symbol": pos.symbol,
            "side": pos.side,
            "qty": pos.qty,
            "entry_price": pos.entry_price,
            "stop_order_id": pos.stop_order_id,
            "tp1_order_id": pos.tp1_order_id,
            "tp2_order_id": pos.tp2_order_id,
            "breakeven_done": pos.breakeven_done,
            "tp1_done": pos.tp1_done,
            "tp2_done": pos.tp2_done,
            "payload": json.dumps(payload),
        }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()

    def get(self, symbol: str) -> ManagedPosition | None:
        sql = """
        SELECT *
        FROM managed_positions
        WHERE symbol = %s
        """

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (symbol,))
                row = cur.fetchone()

        if row is None:
            return None

        return self._row_to_position(row)

    def list_all(self) -> list[ManagedPosition]:
        sql = """
        SELECT *
        FROM managed_positions
        ORDER BY symbol
        """

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        return [self._row_to_position(r) for r in rows]

    def delete(self, symbol: str) -> None:
        sql = """
        DELETE FROM managed_positions
        WHERE symbol = %s
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol,))
            conn.commit()

    def _row_to_position(self, row) -> ManagedPosition:
        return ManagedPosition(
            symbol=row["symbol"],
            side=row["side"],
            qty=float(row["qty"]),
            entry_price=float(row["entry_price"]),
            stop_order_id=row["stop_order_id"],
            tp1_order_id=row["tp1_order_id"],
            tp2_order_id=row["tp2_order_id"],
            breakeven_done=bool(row["breakeven_done"]),
            tp1_done=bool(row["tp1_done"]),
            tp2_done=bool(row["tp2_done"]),
        )
