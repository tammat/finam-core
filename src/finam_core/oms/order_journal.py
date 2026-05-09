from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras

from finam_core.oms.order_state_machine import OrderStateMachine


@dataclass(frozen=True)
class OmsOrderRecord:
    client_order_id: str
    symbol: str
    side: str
    qty: float
    price: float | None
    order_type: str
    status: str


class OmsOrderJournal:
    """Русский комментарий: PostgreSQL-журнал OMS с защитой от дублей client_order_id."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for OmsOrderJournal")
        # Русский комментарий: FSM защищает OMS от невозможных переходов статусов.
        self.state_machine = OrderStateMachine()

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        sql_path = "sql/20260509_oms_order_journal.sql"
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    @staticmethod
    def build_client_order_id(
        *,
        symbol: str,
        side: str,
        qty: float,
        price: float | None,
        strategy: str = "pipeline",
        ts_bucket: str = "manual",
    ) -> str:
        """Русский комментарий: детерминированный idempotency key для заявки."""
        raw = {
            "symbol": symbol,
            "side": side,
            "qty": float(qty),
            "price": None if price is None else float(price),
            "strategy": strategy,
            "ts_bucket": ts_bucket,
        }
        body = json.dumps(raw, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:24]
        return f"oms_{digest}"

    def create_if_absent(
        self,
        *,
        client_order_id: str,
        symbol: str,
        side: str,
        qty: float,
        price: float | None = None,
        order_type: str = "MARKET",
        status: str = "CREATED",
        source: str = "pipeline",
        payload: dict[str, Any] | None = None,
    ) -> tuple[bool, OmsOrderRecord]:
        """Русский комментарий: создаёт заявку один раз; повторный вызов возвращает существующую."""
        self.ensure_schema()
        payload = payload or {}

        sql = """
        INSERT INTO oms_order_journal (
            client_order_id, symbol, side, qty, price, order_type, status, source, payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (client_order_id) DO NOTHING
        RETURNING client_order_id, symbol, side, qty, price, order_type, status;
        """

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    sql,
                    (
                        client_order_id,
                        symbol,
                        side,
                        float(qty),
                        price,
                        order_type,
                        status,
                        source,
                        psycopg2.extras.Json(payload),
                    ),
                )
                row = cur.fetchone()

                if row:
                    return True, OmsOrderRecord(**dict(row))

                cur.execute(
                    """
                    SELECT client_order_id, symbol, side, qty, price, order_type, status
                    FROM oms_order_journal
                    WHERE client_order_id = %s
                    """,
                    (client_order_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    raise RuntimeError("OMS idempotency conflict but existing row not found")

                return False, OmsOrderRecord(**dict(existing))

    def update_status(
        self,
        *,
        client_order_id: str,
        status: str,
        broker_order_id: str | None = None,
    ) -> None:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT status
                    FROM oms_order_journal
                    WHERE client_order_id = %s
                    FOR UPDATE
                    """,
                    (client_order_id,),
                )
                row = cur.fetchone()

                if not row:
                    raise RuntimeError(f"OMS order not found: {client_order_id}")

                current_status = str(row["status"])
                transition = self.state_machine.validate_transition(current_status, status)

                if not transition.allowed:
                    raise RuntimeError(
                        f"OMS invalid status transition: {transition.reason} "
                        f"client_order_id={client_order_id}"
                    )

                cur.execute(
                    """
                    UPDATE oms_order_journal
                    SET status = %s,
                        broker_order_id = COALESCE(%s, broker_order_id),
                        updated_at = now()
                    WHERE client_order_id = %s
                    """,
                    (transition.new_status.value, broker_order_id, client_order_id),
                )

                if cur.rowcount != 1:
                    raise RuntimeError(f"OMS order not found during update: {client_order_id}")
