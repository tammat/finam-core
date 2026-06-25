#!/usr/bin/env python3

print("=== HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("INPUT_SOURCE")
print("canonical_historical_trade_source=public.closed_trades")
print("trade_rows=4073")
print("first_ts=2026-05-04T15:29:21.089519+00:00")
print("last_ts=2026-06-09T09:32:50.915396+00:00")
print("required_columns=symbol,timeframe,entry_ts,exit_ts,net_pnl")

print("")
print("BACKFILL_SCOPE")
print("scope=all_symbol_timeframe_windows_from_public_closed_trades")
print("source_for_features=public.feature_snapshots")
print("target_table=research.market_state_snapshots_v1")
print("target_source=market_state_backfill_closed_trades_v1")

print("")
print("BACKFILL_FLOW")
for step in [
    "extract_distinct_symbol_timeframe_windows",
    "check_feature_snapshots_coverage",
    "derive_market_features_from_feature_snapshots",
    "run_market_state_engine",
    "write_market_state_snapshots_idempotently",
    "rerun_historical_trade_linking",
    "rerun_market_state_pnl_scorecard",
]:
    print(f"STEP name={step}")

print("")
print("SAFETY_GUARDS")
for guard in [
    "research_only",
    "postgres_only",
    "no_sqlite",
    "no_runtime_write",
    "no_execution_write",
    "no_orders",
    "idempotent_snapshot_write_required",
    "closed_trades_are_historical_research_layer_not_micro_live_layer",
]:
    print(f"GUARD name={guard}")

print("")
print("NEXT_STEPS")
print("next=HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_V1")
print("next=HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_IMPLEMENTATION_V1")

print("")
print("VERDICT=HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_PLAN_READY")
