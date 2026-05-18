from __future__ import annotations

import json
from typing import Any


class RuntimeAllocatorDecisionLogger:
    """Русский комментарий: логирует решения allocator v2 для анализа и postmortem."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def log_decision(
        self,
        *,
        symbol: str,
        strategy: str | None,
        regime: str | None,
        base_score: float,
        strategy_weight: float,
        effective_score: float,
        selected: bool,
        decision_reason: str,
        raw_json: dict[str, Any] | None = None,
        source: str = "runtime_universe_allocator_v2",
    ) -> None:
        sql = """
        INSERT INTO runtime_allocator_decisions (
            symbol,
            strategy,
            regime,
            base_score,
            strategy_weight,
            effective_score,
            selected,
            decision_reason,
            source,
            raw_json
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
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
                        base_score,
                        strategy_weight,
                        effective_score,
                        selected,
                        decision_reason,
                        source,
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )
            conn.commit()
