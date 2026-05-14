from __future__ import annotations

import json
import os
from typing import Any

import psycopg2


class TakeProfitEventRepository:
    """Русский комментарий: запись решений TakeProfitEngine в PostgreSQL."""

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
        qty: float | None,
        qty_to_close: float | None,
        price: float | None,
        entry_price: float | None,
        base_stop: float | None,
        take_price: float | None,
        reason: str | None,
        dry_run: bool,
        raw: dict[str, Any] | None = None,
    ) -> None:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO take_profit_events (
                            symbol, action, qty, qty_to_close, price,
                            entry_price, base_stop, take_price, reason, dry_run, raw
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                        """,
                        (
                            symbol,
                            action,
                            float(qty) if qty is not None else None,
                            float(qty_to_close) if qty_to_close is not None else None,
                            float(price) if price is not None else None,
                            float(entry_price) if entry_price is not None else None,
                            float(base_stop) if base_stop is not None else None,
                            float(take_price) if take_price is not None else None,
                            reason,
                            bool(dry_run),
                            json.dumps(raw or {}, ensure_ascii=False, default=str),
                        ),
                    )
        except Exception as exc:
            print(f"TAKE_PROFIT_EVENT_LOG_FAILED error={exc}", flush=True)
