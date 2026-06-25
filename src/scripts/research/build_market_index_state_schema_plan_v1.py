#!/usr/bin/env python3

print("=== MARKET_INDEX_STATE_SCHEMA_PLAN_V1 ===")
print("mode=schema_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("TARGET_TABLES")
print("table=research.market_index_state_context_v1")
print("table=research.market_state_index_context_links_v1")

print("")
print("CONTEXT_SOURCES")
print("context=FX_USDRUB source=public.feature_snapshots")
print("context=ENERGY_BR source=public.feature_snapshots")

print("")
print("PLANNED_COLUMNS_CONTEXT")
for col in [
    "context_id",
    "context_ts",
    "context_code",
    "context_symbol",
    "timeframe",
    "trend_state",
    "volatility_state",
    "session_state",
    "close",
    "canonical_context_signature",
    "compact_context_signature",
    "source",
    "created_at",
]:
    print(f"column={col}")

print("")
print("PLANNED_COLUMNS_LINKS")
for col in [
    "link_id",
    "trade_state_id",
    "trade_id",
    "entry_snapshot_id",
    "entry_compact_signature",
    "context_id",
    "context_code",
    "context_compact_signature",
    "link_quality",
    "link_reason",
    "created_at",
]:
    print(f"column={col}")

print("")
print("DESIGN_RULES")
for rule in [
    "index_context_is_optional",
    "context_signature_is_separate_from_instrument_signature",
    "market_state_baseline_scorecard_remains_valid",
    "context_linking_uses_nearest_prior_context_state",
    "research_only",
    "no_runtime_execution_changes",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=MARKET_INDEX_STATE_SCHEMA_DRY_RUN_V1")

print("")
print("VERDICT=MARKET_INDEX_STATE_SCHEMA_PLAN_READY")
