#!/usr/bin/env python3

print("=== RESEARCH_KNOWLEDGE_BASE_SCHEMA_DRY_RUN_V1 ===")
print("mode=schema_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

ddl = [
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

print("")
print("DDL_DRY_RUN")
for sql in ddl:
    print("SQL_BEGIN")
    print(sql.strip())
    print("SQL_END")

print("")
print("SAFETY_GUARDS")
for guard in [
    "postgres_only",
    "no_sqlite",
    "ddl_print_only",
    "no_db_execute",
    "no_runtime_write",
    "no_execution_write",
    "no_orders",
]:
    print(f"guard={guard}")

print("")
print("DESIGN_RULES")
for rule in [
    "candidate_id_is_immutable",
    "candidate_decisions_are_append_only",
    "candidate_status_current_in_candidates_table",
    "candidate_history_in_decisions_table",
    "hypotheses_are_separate_from_candidates",
    "knowledge_events_capture_all_major_research_decisions",
    "research_only",
    "no_runtime_execution_changes",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_V1")

print("")
print("VERDICT=RESEARCH_KNOWLEDGE_BASE_SCHEMA_DRY_RUN_READY")
