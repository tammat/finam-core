#!/usr/bin/env python3

print("=== GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_DRY_RUN_V1 ===")
print("mode=schema_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

ddl = [
"""
CREATE TABLE IF NOT EXISTS research.analytics_global_edge_scorecard_runs_v1 (
    run_id BIGSERIAL PRIMARY KEY,
    run_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_script TEXT NOT NULL,
    source_checkpoint TEXT,
    rows_total BIGINT NOT NULL DEFAULT 0,
    positive_rows BIGINT NOT NULL DEFAULT 0,
    research_candidates BIGINT NOT NULL DEFAULT 0,
    micro_live_candidates BIGINT NOT NULL DEFAULT 0,
    research_version TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"""
CREATE TABLE IF NOT EXISTS research.analytics_global_edge_scorecard_v1 (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES research.analytics_global_edge_scorecard_runs_v1(run_id),
    symbol TEXT,
    strategy TEXT,
    timeframe TEXT,
    instrument_signature TEXT,
    fx_signature TEXT,
    energy_signature TEXT,
    trades BIGINT NOT NULL DEFAULT 0,
    wins BIGINT NOT NULL DEFAULT 0,
    losses BIGINT NOT NULL DEFAULT 0,
    winrate NUMERIC,
    net_pnl NUMERIC,
    expectancy NUMERIC,
    profit_factor NUMERIC,
    first_trade TIMESTAMPTZ,
    last_trade TIMESTAMPTZ,
    status TEXT NOT NULL,
    reason TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"""
CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_run_v1
ON research.analytics_global_edge_scorecard_v1(run_id);
""",
"""
CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_status_v1
ON research.analytics_global_edge_scorecard_v1(status);
""",
"""
CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_signature_v1
ON research.analytics_global_edge_scorecard_v1(
    instrument_signature,
    fx_signature,
    energy_signature
);
""",
"""
CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_symbol_strategy_v1
ON research.analytics_global_edge_scorecard_v1(symbol, strategy, timeframe);
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
    "scorecard_runs_are_append_only",
    "scorecard_rows_are_versioned_by_run_id",
    "scorecard_persistence_does_not_promote_candidates",
    "research_candidates_seed_from_persisted_scorecard_later",
    "stdout_is_not_source_of_truth",
    "research_only",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_V1")

print("")
print("VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_DRY_RUN_READY")
