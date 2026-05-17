from __future__ import annotations

import json
from typing import Any


class RuntimeUniverseRotationLogger:
    """Русский комментарий: логирует решения по ротации runtime universe в PostgreSQL."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def log_rotation(
        self,
        *,
        symbol: str,
        action: str,
        previous_status: str | None = None,
        new_status: str,
        strategy: str | None = None,
        regime: str | None = None,
        score: float | None = None,
        freshness_adjusted_score: float | None = None,
        reason: str | None = None,
        raw_json: dict[str, Any] | None = None,
    ) -> None:
        sql = """
        insert into runtime_universe_rotation_log (
            symbol,
            strategy,
            regime,
            previous_status,
            new_status,
            action,
            score,
            freshness_adjusted_score,
            reason,
            raw_json,
            created_at
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,now());
        """

        payload = raw_json or {}

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        symbol,
                        strategy,
                        regime,
                        previous_status,
                        new_status,
                        action,
                        score,
                        freshness_adjusted_score,
                        reason,
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )
            conn.commit()
