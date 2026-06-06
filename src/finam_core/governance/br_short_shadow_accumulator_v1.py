from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class BrShortShadowEventV1:
    symbol: str
    side: str
    strategy: str
    signal_id: str | None
    mode: str
    allowed: bool
    shadow_logged: bool
    reason: str
    current_position: Decimal | None = None
    price: Decimal | None = None
    quantity: Decimal | None = None
    payload: dict[str, Any] | None = None


class BrShortShadowAccumulatorV1:
    """
    Русский комментарий:
    Аккумулятор shadow-событий BR short.
    Не влияет на исполнение. Только пишет исследовательские события в PostgreSQL.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set")

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS research_br_short_shadow_signals (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            strategy TEXT NOT NULL DEFAULT '',
            signal_id TEXT,
            mode TEXT NOT NULL DEFAULT 'shadow',
            allowed BOOLEAN NOT NULL DEFAULT false,
            shadow_logged BOOLEAN NOT NULL DEFAULT false,
            reason TEXT NOT NULL DEFAULT '',
            current_position NUMERIC,
            price NUMERIC,
            quantity NUMERIC,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE INDEX IF NOT EXISTS idx_research_br_short_shadow_signals_created
        ON research_br_short_shadow_signals(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_research_br_short_shadow_signals_symbol
        ON research_br_short_shadow_signals(symbol, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_research_br_short_shadow_signals_reason
        ON research_br_short_shadow_signals(reason, created_at DESC);
        """

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def record(self, event: BrShortShadowEventV1) -> None:
        self.migrate()

        sql = """
        INSERT INTO research_br_short_shadow_signals (
            symbol,
            side,
            strategy,
            signal_id,
            mode,
            allowed,
            shadow_logged,
            reason,
            current_position,
            price,
            quantity,
            payload
        )
        VALUES (
            %(symbol)s,
            %(side)s,
            %(strategy)s,
            %(signal_id)s,
            %(mode)s,
            %(allowed)s,
            %(shadow_logged)s,
            %(reason)s,
            %(current_position)s,
            %(price)s,
            %(quantity)s,
            %(payload)s
        )
        """

        payload = event.payload or {}

        params = {
            "symbol": event.symbol,
            "side": event.side,
            "strategy": event.strategy,
            "signal_id": event.signal_id,
            "mode": event.mode,
            "allowed": bool(event.allowed),
            "shadow_logged": bool(event.shadow_logged),
            "reason": event.reason,
            "current_position": event.current_position,
            "price": event.price,
            "quantity": event.quantity,
            "payload": psycopg2.extras.Json(payload),
        }

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
