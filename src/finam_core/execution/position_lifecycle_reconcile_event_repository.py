from __future__ import annotations

import json
import os
from typing import Any

import psycopg2


class PositionLifecycleReconcileEventRepository:
    """Русский комментарий: сохраняет события сверки lifecycle state с фактической позицией."""

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
        strategy: str,
        action: str,
        expected_qty: float | None,
        actual_qty: float | None,
        reason: str,
        raw: dict[str, Any] | None = None,
    ) -> None:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO position_lifecycle_reconcile_events (
                            symbol, strategy, action, expected_qty, actual_qty, reason, raw
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
                        """,
                        (
                            symbol,
                            strategy,
                            action,
                            float(expected_qty) if expected_qty is not None else None,
                            float(actual_qty) if actual_qty is not None else None,
                            reason,
                            json.dumps(raw or {}, ensure_ascii=False, default=str),
                        ),
                    )
        except Exception as exc:
            print(f"POSITION_LIFECYCLE_RECONCILE_EVENT_LOG_FAILED error={exc}", flush=True)
