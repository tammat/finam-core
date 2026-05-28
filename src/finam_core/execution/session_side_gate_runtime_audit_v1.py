from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.execution.session_side_execution_gate_v1 import SessionSideGateDecisionV1


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS session_side_gate_runtime_audit_v1 (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    hour_msk INTEGER NOT NULL,
    session_name TEXT NOT NULL,

    action TEXT NOT NULL,
    allowed BOOLEAN NOT NULL,
    reason TEXT NOT NULL,

    matched_symbol TEXT,
    expectancy_points DOUBLE PRECISION,
    closed_trades INTEGER,

    source TEXT NOT NULL DEFAULT 'paper_pipeline',
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);
"""


INSERT_SQL = """
INSERT INTO session_side_gate_runtime_audit_v1 (
    created_at,
    symbol,
    side,
    hour_msk,
    session_name,
    action,
    allowed,
    reason,
    matched_symbol,
    expectancy_points,
    closed_trades,
    source,
    raw_json
)
VALUES (
    %(created_at)s,
    %(symbol)s,
    %(side)s,
    %(hour_msk)s,
    %(session_name)s,
    %(action)s,
    %(allowed)s,
    %(reason)s,
    %(matched_symbol)s,
    %(expectancy_points)s,
    %(closed_trades)s,
    %(source)s,
    %(raw_json)s
);
"""


class SessionSideGateRuntimeAuditV1:
    """
    Русский комментарий:
    PostgreSQL audit для runtime-решений session-side execution gate.
    Side-effect only: ошибка записи не должна ломать торговый поток.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL") or build_psycopg_url()
        self._ready = False

    def _ensure_table(self) -> None:
        if self._ready:
            return

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_SQL)
            conn.commit()

        self._ready = True

    def save(
        self,
        *,
        decision: SessionSideGateDecisionV1,
        source: str = "paper_pipeline",
        raw: dict | None = None,
    ) -> None:
        self._ensure_table()

        payload = {
            "decision": asdict(decision),
            "raw": raw or {},
        }

        params = {
            "created_at": datetime.now(timezone.utc),
            "symbol": decision.symbol,
            "side": decision.side,
            "hour_msk": int(decision.hour_msk),
            "session_name": decision.session_name,
            "action": decision.action,
            "allowed": bool(decision.allowed),
            "reason": decision.reason,
            "matched_symbol": decision.matched_symbol,
            "expectancy_points": decision.expectancy_points,
            "closed_trades": decision.closed_trades,
            "source": source,
            "raw_json": json.dumps(payload, ensure_ascii=False),
        }

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(INSERT_SQL, params)
            conn.commit()
