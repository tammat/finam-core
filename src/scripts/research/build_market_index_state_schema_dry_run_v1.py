#!/usr/bin/env python3

print("=== MARKET_INDEX_STATE_SCHEMA_DRY_RUN_V1 ===")
print("mode=schema_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

ddl = [
"""
CREATE TABLE IF NOT EXISTS research.market_index_state_context_v1 (
    context_id BIGSERIAL PRIMARY KEY,
    context_ts TIMESTAMPTZ NOT NULL,
    context_code TEXT NOT NULL,
    context_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    trend_state TEXT,
    volatility_state TEXT,
    session_state TEXT,
    close NUMERIC,
    canonical_context_signature TEXT NOT NULL,
    compact_context_signature TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (context_ts, context_code, context_symbol, timeframe, compact_context_signature)
);
""",
"""
CREATE TABLE IF NOT EXISTS research.market_state_index_context_links_v1 (
    link_id BIGSERIAL PRIMARY KEY,
    trade_state_id BIGINT NOT NULL REFERENCES research.trade_state_snapshots_v1(trade_state_id),
    trade_id TEXT NOT NULL,
    entry_snapshot_id BIGINT REFERENCES research.market_state_snapshots_v1(snapshot_id),
    entry_compact_signature TEXT,
    context_id BIGINT REFERENCES research.market_index_state_context_v1(context_id),
    context_code TEXT NOT NULL,
    context_compact_signature TEXT,
    link_quality TEXT NOT NULL,
    link_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trade_state_id, context_code)
);
""",
"""
CREATE INDEX IF NOT EXISTS idx_market_index_state_context_lookup_v1
ON research.market_index_state_context_v1(context_code, context_symbol, timeframe, context_ts);
""",
"""
CREATE INDEX IF NOT EXISTS idx_market_index_state_context_signature_v1
ON research.market_index_state_context_v1(context_code, compact_context_signature);
""",
"""
CREATE INDEX IF NOT EXISTS idx_market_state_index_context_links_trade_v1
ON research.market_state_index_context_links_v1(trade_id);
""",
"""
CREATE INDEX IF NOT EXISTS idx_market_state_index_context_links_context_v1
ON research.market_state_index_context_links_v1(context_code, context_compact_signature);
""",
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
    "index_context_is_optional",
    "context_signature_is_separate_from_instrument_signature",
    "context_linking_is_additional_dimension",
    "idempotent_schema",
    "no_runtime_execution_changes",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=MARKET_INDEX_STATE_SCHEMA_APPLY_V1")

print("")
print("VERDICT=MARKET_INDEX_STATE_SCHEMA_DRY_RUN_READY")
