from __future__ import annotations

from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class RuntimeStateGateDecision:
    allowed: bool
    reason: str


class RuntimeStateGate:
    """Русский комментарий: запрещает создание заявок, если runtime state не ACTIVE."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def check(self, *, symbol: str, strategy: str, timeframe: str) -> RuntimeStateGateDecision:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT runtime_state, allow_new_entries, state_reason
                    FROM ng_live_runtime_state
                    WHERE symbol=%s
                      AND strategy=%s
                      AND timeframe=%s
                    LIMIT 1
                """, (symbol, strategy, timeframe))
                row = cur.fetchone()

        if not row:
            return RuntimeStateGateDecision(False, "runtime_state_missing")

        runtime_state, allow_new_entries, state_reason = row

        if str(runtime_state) != "ACTIVE" or not bool(allow_new_entries):
            return RuntimeStateGateDecision(
                False,
                f"runtime_state_block state={runtime_state} allow_new_entries={allow_new_entries} reason={state_reason}",
            )

        return RuntimeStateGateDecision(True, "runtime_state_active")
