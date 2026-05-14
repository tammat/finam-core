from __future__ import annotations

import json
import os
from typing import Any

import psycopg2


class TrailingOrderEventRepository:
    """Русский комментарий: запись решений trailing stop manager в PostgreSQL."""

    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        if not self.database_url:
            db_host = os.getenv("DB_HOST", "127.0.0.1")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "finam_core")
            db_user = os.getenv("DB_USER", "finam")
            db_password = os.getenv("DB_PASSWORD", "finam")
            self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    def log_event(
        self,
        *,
        symbol: str,
        action: str,
        side: str | None,
        qty: float | None,
        stop_price: float | None,
        reason: str | None,
        dry_run: bool,
        raw: dict[str, Any] | None = None,
    ) -> None:
        if not self.database_url:
            return

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trailing_order_events (
                            symbol, action, side, qty, stop_price, reason, dry_run, raw
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                        """,
                        (
                            symbol,
                            action,
                            side,
                            float(qty) if qty is not None else None,
                            float(stop_price) if stop_price is not None else None,
                            reason,
                            bool(dry_run),
                            json.dumps(raw or {}, ensure_ascii=False, default=str),
                        ),
                    )
        except Exception as exc:
            print(f"TRAILING_ORDER_EVENT_LOG_FAILED error={exc}", flush=True)
