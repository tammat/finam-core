#!/usr/bin/env python3

print("=== MARKET_STATE_LINK_COVERAGE_REPAIR_PLAN_V1 ===")
print("mode=repair_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("\nPROBLEM")
print("linked_total=44")
print("link_ok=0")
print("no_snapshot=44")
print("root_cause=trade_timestamps_do_not_have_matching_prior_market_state_snapshots")
print("effect=MARKET_STATE_PNL_SCORECARD_NO_LINKED_PNL_ROWS")

print("\nREPAIR_HYPOTHESES")
items = [
    "timeframe_mismatch_between_trade_outcomes_and_market_state_snapshots",
    "symbol_mismatch_between_trade_outcomes_and_market_state_snapshots",
    "snapshot_time_window_too_narrow_or_snapshots_start_after_trades",
    "live_shadow_feed_contains_test_rows_only",
    "trade_outcomes_are_historical_but_market_state_snapshots_are_live_shadow_only",
]
for item in items:
    print(f"HYPOTHESIS name={item}")

print("\nREPAIR_ACTIONS")
actions = [
    "audit_trade_outcomes_symbol_timeframe_ts_distribution",
    "audit_market_state_snapshot_symbol_timeframe_ts_distribution",
    "compare_trade_entry_ts_to_snapshot_ts_ranges",
    "add_nearest_snapshot_age_diagnostics",
    "decide_between_backfill_market_states_for_trade_window_or_restrict_scorecard_to_shadow_period",
]
for action in actions:
    print(f"ACTION name={action}")

print("\nSAFETY_GUARDS")
guards = [
    "repair_plan_is_read_only",
    "no_runtime_write",
    "no_execution_write",
    "no_orders",
    "no_micro_live_candidate_until_link_ok_positive",
]
for guard in guards:
    print(f"GUARD name={guard}")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_V1")
print("next=MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_V1")

print("\nVERDICT=MARKET_STATE_LINK_COVERAGE_REPAIR_PLAN_READY")
