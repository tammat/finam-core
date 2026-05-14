from __future__ import annotations

import json
import os
from typing import Any

import psycopg2


class PositionLifecycleStateRepository:
    """
    Русский комментарий:
    Persistent lifecycle state позиции.

    Нужен для:
    - restart recovery
    - partial close continuity
    - trailing continuity
    - broker reconciliation
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.enabled = bool(self.database_url)

    def upsert_state(
        self,
        *,
        symbol: str,
        strategy: str = "default",
        entry_price: float | None = None,
        initial_qty: float | None = None,
        remaining_qty: float | None = None,
        tp1_done: bool | None = None,
        tp2_done: bool | None = None,
        profit_lock_done: bool | None = None,
        trailing_active: bool | None = None,
        current_stop: float | None = None,
        current_take_profit: float | None = None,
        raw: dict[str, Any] | None = None,
    ) -> int | None:
        if not self.enabled:
            return None

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO position_lifecycle_state (
                            symbol,
                            strategy,
                            entry_price,
                            initial_qty,
                            remaining_qty,
                            tp1_done,
                            tp2_done,
                            profit_lock_done,
                            trailing_active,
                            current_stop,
                            current_take_profit,
                            raw
                        )
                        VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                        ON CONFLICT (symbol, strategy)
                        DO UPDATE SET
                            entry_price = EXCLUDED.entry_price,
                            initial_qty = EXCLUDED.initial_qty,
                            remaining_qty = EXCLUDED.remaining_qty,
                            tp1_done = EXCLUDED.tp1_done,
                            tp2_done = EXCLUDED.tp2_done,
                            profit_lock_done = EXCLUDED.profit_lock_done,
                            trailing_active = EXCLUDED.trailing_active,
                            current_stop = EXCLUDED.current_stop,
                            current_take_profit = EXCLUDED.current_take_profit,
                            raw = COALESCE(position_lifecycle_state.raw, '{}'::jsonb)
                                  || COALESCE(EXCLUDED.raw, '{}'::jsonb),
                            updated_at = NOW()
                        RETURNING id
                        """,
                        (
                            symbol,
                            strategy,
                            entry_price,
                            initial_qty,
                            remaining_qty,
                            tp1_done,
                            tp2_done,
                            profit_lock_done,
                            trailing_active,
                            current_stop,
                            current_take_profit,
                            json.dumps(raw or {}, ensure_ascii=False),
                        ),
                    )

                    row = cur.fetchone()
                    return int(row[0]) if row else None

        except Exception as exc:
            print(f"POSITION_LIFECYCLE_STATE_UPSERT_FAILED error={exc}", flush=True)
            return None

    def load_state(
        self,
        *,
        symbol: str,
        strategy: str = "default",
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            symbol,
                            strategy,
                            entry_price,
                            initial_qty,
                            remaining_qty,
                            tp1_done,
                            tp2_done,
                            profit_lock_done,
                            trailing_active,
                            current_stop,
                            current_take_profit,
                            raw
                        FROM position_lifecycle_state
                        WHERE symbol = %s
                          AND strategy = %s
                        """,
                        (symbol, strategy),
                    )

                    row = cur.fetchone()
                    if not row:
                        return None

                    return {
                        "symbol": row[0],
                        "strategy": row[1],
                        "entry_price": row[2],
                        "initial_qty": row[3],
                        "remaining_qty": row[4],
                        "tp1_done": row[5],
                        "tp2_done": row[6],
                        "profit_lock_done": row[7],
                        "trailing_active": row[8],
                        "current_stop": row[9],
                        "current_take_profit": row[10],
                        "raw": row[11] or {},
                    }

        except Exception as exc:
            print(f"POSITION_LIFECYCLE_STATE_LOAD_FAILED error={exc}", flush=True)
            return None

    def delete_state(
        self,
        *,
        symbol: str,
        strategy: str = "default",
    ) -> bool:
        """Русский комментарий: удаляет lifecycle state после закрытия позиции."""
        if not self.enabled:
            return False

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM position_lifecycle_state
                        WHERE symbol = %s
                          AND strategy = %s
                        """,
                        (symbol, strategy),
                    )
                    return cur.rowcount > 0
        except Exception as exc:
            print(f"POSITION_LIFECYCLE_STATE_DELETE_FAILED error={exc}", flush=True)
            return False

