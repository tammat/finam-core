from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS risk_event_audit_v1 (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    category TEXT NOT NULL,
    severity TEXT NOT NULL,

    symbol TEXT NOT NULL,
    strategy TEXT,
    timeframe TEXT,

    decision TEXT NOT NULL,
    reason TEXT NOT NULL,

    value DOUBLE PRECISION,
    exposure DOUBLE PRECISION,
    risk_limit DOUBLE PRECISION,

    routed BOOLEAN NOT NULL DEFAULT false,
    channel TEXT,
    skipped_reason TEXT,

    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_risk_event_audit_v1_created_at
ON risk_event_audit_v1(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_risk_event_audit_v1_symbol
ON risk_event_audit_v1(symbol);

CREATE INDEX IF NOT EXISTS idx_risk_event_audit_v1_severity
ON risk_event_audit_v1(severity);

CREATE INDEX IF NOT EXISTS idx_risk_event_audit_v1_category
ON risk_event_audit_v1(category);
"""


@dataclass(frozen=True)
class RiskEventAuditRecordV1:
    category: str
    severity: str
    symbol: str
    strategy: str | None
    timeframe: str | None
    decision: str
    reason: str
    value: float | None
    exposure: float | None
    risk_limit: float | None
    routed: bool
    channel: str | None
    skipped_reason: str | None
    raw: dict[str, Any] | None = None


class RiskEventAuditStorageV1:
    """
    Русский комментарий:
    Audit storage для risk notification pipeline.
    Не влияет на execution flow.
    """

    def __init__(self, *, database_url: str | None = None) -> None:
        self.database_url = database_url or build_psycopg_url()

    def ensure_schema(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
            conn.commit()

        print("RISK_EVENT_AUDIT_STORAGE_SCHEMA_OK", flush=True)

    def insert_event(self, record: RiskEventAuditRecordV1) -> int:
        sql = """
        INSERT INTO risk_event_audit_v1 (
            category,
            severity,
            symbol,
            strategy,
            timeframe,
            decision,
            reason,
            value,
            exposure,
            risk_limit,
            routed,
            channel,
            skipped_reason,
            raw_json
        )
        VALUES (
            %(category)s,
            %(severity)s,
            %(symbol)s,
            %(strategy)s,
            %(timeframe)s,
            %(decision)s,
            %(reason)s,
            %(value)s,
            %(exposure)s,
            %(risk_limit)s,
            %(routed)s,
            %(channel)s,
            %(skipped_reason)s,
            %(raw_json)s
        )
        RETURNING id;
        """

        payload = {
            "category": record.category,
            "severity": record.severity,
            "symbol": record.symbol,
            "strategy": record.strategy,
            "timeframe": record.timeframe,
            "decision": record.decision,
            "reason": record.reason,
            "value": record.value,
            "exposure": record.exposure,
            "risk_limit": record.risk_limit,
            "routed": record.routed,
            "channel": record.channel,
            "skipped_reason": record.skipped_reason,
            "raw_json": json.dumps(record.raw or {}),
        }

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, payload)
                row = cur.fetchone()
            conn.commit()

        inserted_id = int(row["id"])

        print(
            "RISK_EVENT_AUDIT_STORAGE_INSERT_OK",
            f"id={inserted_id}",
            f"severity={record.severity}",
            f"symbol={record.symbol}",
            f"decision={record.decision}",
            flush=True,
        )

        return inserted_id
