from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras

from finam_core.projections.projection_engine import ProjectionState


class ProjectionStore:
    """Русский комментарий: сохраняет materialized projections в PostgreSQL."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for ProjectionStore")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        with open("sql/20260510_projection_store.sql", "r", encoding="utf-8") as f:
            sql = f.read()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def save(self, state: ProjectionState) -> None:
        """Русский комментарий: upsert всех projections."""
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor() as cur:
                for order_id, order_state in state.orders.orders.items():
                    cur.execute(
                        """
                        INSERT INTO order_projection (order_id, state, updated_at)
                        VALUES (%s, %s, now())
                        ON CONFLICT (order_id)
                        DO UPDATE SET state = EXCLUDED.state, updated_at = now()
                        """,
                        (str(order_id), psycopg2.extras.Json(order_state)),
                    )

                for symbol, position_state in state.positions.positions.items():
                    cur.execute(
                        """
                        INSERT INTO position_projection (symbol, state, updated_at)
                        VALUES (%s, %s, now())
                        ON CONFLICT (symbol)
                        DO UPDATE SET state = EXCLUDED.state, updated_at = now()
                        """,
                        (str(symbol), psycopg2.extras.Json(position_state)),
                    )

                portfolio_state = {
                    "cash_delta": state.portfolio.cash_delta,
                    "realized_pnl": state.portfolio.realized_pnl,
                    "exposure": state.portfolio.exposure,
                    "events_processed": state.events_processed,
                }

                cur.execute(
                    """
                    INSERT INTO portfolio_projection (id, state, updated_at)
                    VALUES ('GLOBAL', %s, now())
                    ON CONFLICT (id)
                    DO UPDATE SET state = EXCLUDED.state, updated_at = now()
                    """,
                    (psycopg2.extras.Json(portfolio_state),),
                )

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT state FROM order_projection WHERE order_id = %s", (order_id,))
                row = cur.fetchone()

        return dict(row["state"]) if row else None

    def get_position(self, symbol: str) -> dict[str, Any] | None:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT state FROM position_projection WHERE symbol = %s", (symbol,))
                row = cur.fetchone()

        return dict(row["state"]) if row else None

    def get_portfolio(self) -> dict[str, Any] | None:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT state FROM portfolio_projection WHERE id = 'GLOBAL'")
                row = cur.fetchone()

        return dict(row["state"]) if row else None
