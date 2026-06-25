#!/usr/bin/env python3

import os
import sys
import psycopg2


DDL = [
"""
CREATE TABLE IF NOT EXISTS research.research_candidates_v1 (
    candidate_id TEXT PRIMARY KEY,
    candidate_version INTEGER NOT NULL DEFAULT 1,
    candidate_type TEXT NOT NULL,
    instrument_signature TEXT,
    fx_signature TEXT,
    energy_signature TEXT,
    session_signature TEXT,
    symbol TEXT,
    strategy TEXT,
    timeframe TEXT,
    trade_count BIGINT,
    winrate NUMERIC,
    expectancy NUMERIC,
    profit_factor NUMERIC,
    net_pnl NUMERIC,
    commission NUMERIC,
    max_drawdown NUMERIC,
    validation_level TEXT,
    status TEXT NOT NULL,
    status_reason TEXT,
    discovered_at TIMESTAMPTZ,
    last_validation_at TIMESTAMPTZ,
    created_by_script TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"""
CREATE TABLE IF NOT EXISTS research.research_candidate_decisions_v1 (
    decision_id BIGSERIAL PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES research.research_candidates_v1(candidate_id),
    decision_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    old_status TEXT,
    new_status TEXT NOT NULL,
    decision_reason TEXT NOT NULL,
    decision_detail TEXT,
    decided_by_script TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"""
CREATE TABLE IF NOT EXISTS research.research_hypotheses_v1 (
    hypothesis_id BIGSERIAL PRIMARY KEY,
    hypothesis_code TEXT NOT NULL UNIQUE,
    hypothesis_type TEXT NOT NULL,
    hypothesis_text_ru TEXT NOT NULL,
    status TEXT NOT NULL,
    status_reason TEXT,
    linked_candidate_id TEXT REFERENCES research.research_candidates_v1(candidate_id),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_script TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"""
CREATE TABLE IF NOT EXISTS research.research_knowledge_events_v1 (
    event_id BIGSERIAL PRIMARY KEY,
    event_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT,
    event_summary_ru TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_script TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"""
CREATE INDEX IF NOT EXISTS idx_research_candidates_status_v1
ON research.research_candidates_v1(status);
""",
"""
CREATE INDEX IF NOT EXISTS idx_research_candidates_signature_v1
ON research.research_candidates_v1(instrument_signature, fx_signature, energy_signature, session_signature);
""",
"""
CREATE INDEX IF NOT EXISTS idx_research_candidate_decisions_candidate_v1
ON research.research_candidate_decisions_v1(candidate_id, decision_ts);
""",
"""
CREATE INDEX IF NOT EXISTS idx_research_knowledge_events_object_v1
ON research.research_knowledge_events_v1(object_type, object_id, event_ts);
"""
]


def main() -> int:
    print("=== RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_V1 ===")
    print("mode=schema_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    if "--apply" not in sys.argv:
        print("db_update=0")
        print("VERDICT=RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_REQUIRES_APPLY_FLAG")
        return 2

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            for sql in DDL:
                cur.execute(sql)
        conn.commit()

    print("db_update=1")
    print("tables_applied=4")
    print("indexes_applied=4")
    print("schema=research")
    print("VERDICT=RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
