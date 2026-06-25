#!/usr/bin/env python3

print("=== MARKET_STATE_TRADE_LINKING_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("\nPURPOSE")
print("purpose=link_market_state_snapshots_to_clean_trade_facts")
print("purpose=prepare_state_pnl_scorecard")
print("purpose=enable_edge_analysis_after_trade_state_linking")

print("\nINPUTS")
inputs = [
    "research.market_state_snapshots_v1",
    "research.market_state_snapshot_values_v1",
    "clean_trade_facts",
    "payload.trade_source_class=RUNTIME_OR_PAPER_CLEAN_ENOUGH",
]
for item in inputs:
    print(f"INPUT name={item}")

print("\nLINKING_RULES")
rules = [
    "link_trade_entry_to_nearest_prior_snapshot",
    "link_trade_exit_to_nearest_prior_snapshot",
    "symbol_must_match",
    "timeframe_must_match_when_available",
    "entry_snapshot_ts_lte_trade_ts",
    "exit_snapshot_ts_lte_trade_ts",
    "max_snapshot_age_required",
    "do_not_link_historical_replay_to_micro_live_layer",
    "do_not_link_legacy_backfill_to_clean_edge",
]
for rule in rules:
    print(f"LINK_RULE name={rule}")

print("\nTARGET_TABLES")
tables = [
    "research.trade_state_snapshots_v1",
]
for table in tables:
    print(f"TABLE name={table}")

print("\nPLANNED_COLUMNS")
columns = [
    "trade_id",
    "symbol",
    "timeframe",
    "entry_ts",
    "exit_ts",
    "entry_snapshot_id",
    "exit_snapshot_id",
    "entry_compact_signature",
    "exit_compact_signature",
    "holding_snapshot_count",
    "link_quality",
    "link_reason",
    "created_at",
]
for col in columns:
    print(f"COLUMN name={col}")

print("\nLINK_QUALITY")
qualities = [
    "EXACT_OR_NEAREST_OK",
    "ENTRY_ONLY",
    "EXIT_ONLY",
    "NO_SNAPSHOT",
    "STALE_SNAPSHOT",
    "SYMBOL_MISMATCH",
]
for q in qualities:
    print(f"QUALITY code={q}")

print("\nSAFETY_GUARDS")
guards = [
    "research_only",
    "postgres_only",
    "no_sqlite",
    "no_runtime_write",
    "no_execution_write",
    "no_orders",
    "clean_trade_source_filter_required",
    "idempotent_linking_required",
]
for guard in guards:
    print(f"GUARD name={guard}")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_TRADE_LINKING_SCHEMA_DRY_RUN_V1")
print("next=MARKET_STATE_TRADE_LINKING_IMPLEMENTATION_V1")
print("next=MARKET_STATE_PNL_SCORECARD_V1")

print("\nVERDICT=MARKET_STATE_TRADE_LINKING_PLAN_READY")
