#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_V1
#
# Dry-run DDL для таблиц Market State Engine.
#
# ВАЖНО:
# - SQL только печатается;
# - БД не изменяется;
# - Runtime не изменяется;
# - Execution не изменяется.
# ==========================================================

print("=== MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_V1 ===")
print("mode=schema_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

ddl = [
    """
CREATE SCHEMA IF NOT EXISTS research;
""",
    """
CREATE TABLE IF NOT EXISTS research.market_state_snapshots_v1 (
    snapshot_id BIGSERIAL PRIMARY KEY,
    snapshot_ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT,
    timeframe TEXT NOT NULL,
    canonical_signature TEXT NOT NULL,
    compact_signature TEXT NOT NULL,
    quality TEXT NOT NULL,
    confidence NUMERIC,
    conflict_score NUMERIC,
    source TEXT NOT NULL DEFAULT 'market_state_engine_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_ts, symbol, timeframe, compact_signature)
);
""",
    """
CREATE TABLE IF NOT EXISTS research.market_state_snapshot_values_v1 (
    snapshot_value_id BIGSERIAL PRIMARY KEY,
    snapshot_id BIGINT NOT NULL REFERENCES research.market_state_snapshots_v1(snapshot_id),
    state_group TEXT NOT NULL,
    state_code TEXT NOT NULL,
    confidence NUMERIC,
    classifier_version TEXT,
    explanation_ru TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_id, state_group)
);
""",
    """
CREATE TABLE IF NOT EXISTS research.market_state_snapshot_metadata_v1 (
    snapshot_id BIGINT PRIMARY KEY REFERENCES research.market_state_snapshots_v1(snapshot_id),
    ontology_version TEXT NOT NULL,
    research_version TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    classifier_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
    explanation_tree_ru JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NOT NULL DEFAULT 'market_state_engine_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
    """
CREATE TABLE IF NOT EXISTS research.market_state_transitions_v1 (
    transition_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    snapshot_from BIGINT NOT NULL REFERENCES research.market_state_snapshots_v1(snapshot_id),
    snapshot_to BIGINT NOT NULL REFERENCES research.market_state_snapshots_v1(snapshot_id),
    transition_type TEXT NOT NULL,
    duration_seconds BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_from, snapshot_to)
);
""",
    """
CREATE INDEX IF NOT EXISTS idx_market_state_snapshots_symbol_ts
ON research.market_state_snapshots_v1(symbol, snapshot_ts);
""",
    """
CREATE INDEX IF NOT EXISTS idx_market_state_snapshots_compact_signature
ON research.market_state_snapshots_v1(compact_signature);
""",
    """
CREATE INDEX IF NOT EXISTS idx_market_state_snapshot_values_snapshot
ON research.market_state_snapshot_values_v1(snapshot_id);
""",
]

print("\nDDL_DRY_RUN")
for statement in ddl:
    cleaned = statement.strip()
    print("SQL_BEGIN")
    print(cleaned)
    print("SQL_END")

print("\nSAFETY_GUARDS")
print("guard=postgres_only")
print("guard=no_sqlite")
print("guard=ddl_print_only")
print("guard=no_db_execute")
print("guard=no_runtime_write")
print("guard=no_execution_write")

print("\nDESIGN_RULES")
print("rule=snapshots_are_immutable")
print("rule=snapshot_values_are_rows")
print("rule=metadata_versions_required")
print("rule=canonical_signature_required")
print("rule=compact_signature_required")
print("rule=idempotent_schema")
print("rule=no_runtime_execution_changes")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_V1")
print("next=MARKET_STATE_ENGINE_DATABASE_WRITER_IMPLEMENTATION_V1")

print("\nVERDICT=MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_READY")
