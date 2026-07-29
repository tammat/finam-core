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
                        "SELECT analytics.resolve_paper_portfolio_scope_v1(%s,'paper')",
                        (symbol,),
                    )
                    portfolio_scope = cur.fetchone()[0]
                    if not portfolio_scope:
                        return None
                    cur.execute(
                        """
                        INSERT INTO analytics.paper_research_position_lifecycle_v1 (
                            portfolio_scope,
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
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                        ON CONFLICT (portfolio_scope, symbol, strategy)
                        DO UPDATE SET
                            entry_price = COALESCE(EXCLUDED.entry_price, paper_research_position_lifecycle_v1.entry_price),
                            initial_qty = COALESCE(EXCLUDED.initial_qty, paper_research_position_lifecycle_v1.initial_qty),
                            remaining_qty = COALESCE(EXCLUDED.remaining_qty, paper_research_position_lifecycle_v1.remaining_qty),
                            tp1_done = COALESCE(EXCLUDED.tp1_done, paper_research_position_lifecycle_v1.tp1_done),
                            tp2_done = COALESCE(EXCLUDED.tp2_done, paper_research_position_lifecycle_v1.tp2_done),
                            profit_lock_done = COALESCE(EXCLUDED.profit_lock_done, paper_research_position_lifecycle_v1.profit_lock_done),
                            trailing_active = COALESCE(EXCLUDED.trailing_active, paper_research_position_lifecycle_v1.trailing_active),
                            current_stop = COALESCE(EXCLUDED.current_stop, paper_research_position_lifecycle_v1.current_stop),
                            current_take_profit = COALESCE(EXCLUDED.current_take_profit, paper_research_position_lifecycle_v1.current_take_profit),
                            raw = COALESCE(paper_research_position_lifecycle_v1.raw, '{}'::jsonb)
                                  || COALESCE(EXCLUDED.raw, '{}'::jsonb),
                            updated_at = NOW()
                        RETURNING id
                        """,
                        (
                            portfolio_scope,
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
                        "SELECT analytics.resolve_paper_portfolio_scope_v1(%s,'paper')",
                        (symbol,),
                    )
                    portfolio_scope = cur.fetchone()[0]
                    if not portfolio_scope:
                        return None
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
                        FROM analytics.paper_research_position_lifecycle_v1
                        WHERE portfolio_scope = %s
                          AND symbol = %s
                          AND strategy = %s
                        """,
                        (portfolio_scope, symbol, strategy),
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
                        "SELECT analytics.resolve_paper_portfolio_scope_v1(%s,'paper')",
                        (symbol,),
                    )
                    portfolio_scope = cur.fetchone()[0]
                    if not portfolio_scope:
                        return False
                    cur.execute(
                        """
                        DELETE FROM analytics.paper_research_position_lifecycle_v1
                        WHERE portfolio_scope = %s
                          AND symbol = %s
                          AND strategy = %s
                        """,
                        (portfolio_scope, symbol, strategy),
                    )
                    return cur.rowcount > 0
        except Exception as exc:
            print(f"POSITION_LIFECYCLE_STATE_DELETE_FAILED error={exc}", flush=True)
            return False
