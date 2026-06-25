#!/usr/bin/env python3

print("=== MARKET_STATE_TRADE_LINKING_SCHEMA_DRY_RUN_V1 ===")
print("mode=schema_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

ddl = [
    """
CREATE TABLE IF NOT EXISTS research.trade_state_snapshots_v1 (
    trade_state_id BIGSERIAL PRIMARY KEY,
    trade_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT,
    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,
    entry_snapshot_id BIGINT REFERENCES research.market_state_snapshots_v1(snapshot_id),
    exit_snapshot_id BIGINT REFERENCES research.market_state_snapshots_v1(snapshot_id),
    entry_compact_signature TEXT,
    exit_compact_signature TEXT,
    holding_snapshot_count BIGINT,
    link_quality TEXT NOT NULL,
    link_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trade_id)
);
""",
    """
CREATE INDEX IF NOT EXISTS idx_trade_state_snapshots_trade_id
ON research.trade_state_snapshots_v1(trade_id);
""",
    """
CREATE INDEX IF NOT EXISTS idx_trade_state_snapshots_symbol_entry_ts
ON research.trade_state_snapshots_v1(symbol, entry_ts);
""",
    """
CREATE INDEX IF NOT EXISTS idx_trade_state_snapshots_entry_signature
ON research.trade_state_snapshots_v1(entry_compact_signature);
""",
]

print("\nDDL_DRY_RUN")
for statement in ddl:
    print("SQL_BEGIN")
    print(statement.strip())
    print("SQL_END")

print("\nSAFETY_GUARDS")
print("guard=postgres_only")
print("guard=no_sqlite")
print("guard=ddl_print_only")
print("guard=no_db_execute")
print("guard=no_runtime_write")
print("guard=no_execution_write")

print("\nDESIGN_RULES")
print("rule=idempotent_schema")
print("rule=trade_id_unique")
print("rule=entry_and_exit_snapshots_optional")
print("rule=link_quality_required")
print("rule=no_runtime_execution_changes")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_TRADE_LINKING_SCHEMA_APPLY_V1")

print("\nVERDICT=MARKET_STATE_TRADE_LINKING_SCHEMA_DRY_RUN_READY")
