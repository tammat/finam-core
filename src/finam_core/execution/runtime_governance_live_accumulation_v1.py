from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class RuntimeGovernanceLiveDecisionV1:
    symbol: str
    side: str
    hour_msk: int
    allowed: bool
    action: str
    reason: str
    session_action: str | None = None
    strict_reason: str | None = None
    decay_state: str | None = None
    expectancy_points: float | None = None
    closed_trades: int | None = None
    raw_json: dict[str, Any] | None = None


class RuntimeGovernanceLiveAccumulatorV1:
    """
    Русский комментарий:
    Накопитель фактических runtime governance решений.
    Не принимает торговых решений и не блокирует заявки.
    Только пишет ALLOW / SOFT_BLOCK / FAILED_OPEN в PostgreSQL.
    """

    CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS runtime_governance_live_accumulation_v1 (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        hour_msk INTEGER NOT NULL,
        allowed BOOLEAN NOT NULL,
        action TEXT NOT NULL,
        reason TEXT NOT NULL,
        session_action TEXT,
        strict_reason TEXT,
        decay_state TEXT,
        expectancy_points DOUBLE PRECISION,
        closed_trades INTEGER,
        raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
    );
    """

    INSERT_SQL = """
    INSERT INTO runtime_governance_live_accumulation_v1 (
        created_at,
        symbol,
        side,
        hour_msk,
        allowed,
        action,
        reason,
        session_action,
        strict_reason,
        decay_state,
        expectancy_points,
        closed_trades,
        raw_json
    )
    VALUES (
        %(created_at)s,
        %(symbol)s,
        %(side)s,
        %(hour_msk)s,
        %(allowed)s,
        %(action)s,
        %(reason)s,
        %(session_action)s,
        %(strict_reason)s,
        %(decay_state)s,
        %(expectancy_points)s,
        %(closed_trades)s,
        %(raw_json)s::jsonb
    );
    """

    def ensure_schema(self) -> None:
        with psycopg.connect(build_psycopg_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(self.CREATE_SQL)
            conn.commit()

    def append(self, decision: RuntimeGovernanceLiveDecisionV1) -> None:
        self.ensure_schema()

        payload = {
            "created_at": datetime.now(timezone.utc),
            "symbol": decision.symbol,
            "side": decision.side,
            "hour_msk": decision.hour_msk,
            "allowed": decision.allowed,
            "action": decision.action,
            "reason": decision.reason,
            "session_action": decision.session_action,
            "strict_reason": decision.strict_reason,
            "decay_state": decision.decay_state,
            "expectancy_points": decision.expectancy_points,
            "closed_trades": decision.closed_trades,
            "raw_json": json.dumps(decision.raw_json or {}, ensure_ascii=False),
        }

        with psycopg.connect(build_psycopg_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(self.INSERT_SQL, payload)
            conn.commit()
