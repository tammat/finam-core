#!/usr/bin/env python3

print("=== MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_V1 ===")
print("mode=backfill_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("TARGET_WINDOW")
print("target_symbol=BRN6@RTSX")
print("target_timeframe=M5")
print("target_window_start=2026-05-18T00:00:00+00:00")
print("target_window_end=2026-05-27T23:59:59+00:00")
print("reason=trade_outcomes_window_has_no_matching_market_state_snapshots")

print("")
print("BACKFILL_SOURCE")
print("source=market_bars")
print("required_columns=symbol,timeframe,ts,open,high,low,close,volume")
print("fallback_source=existing_feature_snapshot_if_market_bars_unavailable")
print("source_validation_required=1")

print("")
print("BACKFILL_FLOW")
steps = [
    "load_market_bars_for_target_window",
    "derive_minimal_market_features",
    "run_market_state_engine",
    "write_market_state_snapshots_to_research_schema",
    "rerun_trade_linking",
    "rerun_market_state_pnl_scorecard",
]
for step in steps:
    print(f"STEP name={step}")

print("")
print("FEATURES_V1")
features = [
    "symbol",
    "timeframe",
    "close",
    "trend_from_close_slope_or_unknown",
    "volatility_from_range_or_unknown",
    "session_from_timestamp",
]
for feature in features:
    print(f"FEATURE name={feature}")

print("")
print("SAFETY_GUARDS")
guards = [
    "backfill_is_research_only",
    "postgres_only",
    "no_sqlite",
    "no_runtime_write",
    "no_execution_write",
    "no_orders",
    "idempotent_snapshot_write_required",
]
for guard in guards:
    print(f"GUARD name={guard}")

print("")
print("NEXT_STEPS")
print("next=MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_V1")
print("next=MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_IMPLEMENTATION_V1")

print("")
print("VERDICT=MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_READY")
