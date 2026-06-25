#!/usr/bin/env python3

print("=== GLOBAL_LINK_REPAIR_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("INPUT_DIAGNOSIS")
print("closed_trades=437")
print("linked=201")
print("lost=236")
print("coverage=0.4599")
print("root_cause=NO_FEATURE_SNAPSHOT")
print("root_cause_count=236")

print("")
print("LOSS_DISTRIBUTION")
print("symbol=BRM6@RTSX trades=119 linked=119 lost=0 coverage=1.0000")
print("symbol=BRN6@RTSX trades=130 linked=53 lost=77 coverage=0.4077")
print("symbol=NGN6@RTSX trades=188 linked=29 lost=159 coverage=0.1543")

print("")
print("REPAIR_DECISION")
print("decision=BACKFILL_FEATURE_SNAPSHOTS_THEN_REBUILD_MARKET_STATES")
print("target_1=NGN6@RTSX")
print("target_2=BRN6@RTSX")
print("required_timeframes=M1,LIVE")
print("repair_priority=P1")
print("reason=lost_trades_are_from_core_research_futures")
print("reason=global_context_linking_blocked_until_coverage_repaired")

print("")
print("REPAIR_FLOW")
for step in [
    "discover_available_raw_bar_sources_for_NGN6_BRN6",
    "backfill_missing_feature_snapshots_for_trade_windows",
    "rerun_universe_backfill_for_repaired_symbols",
    "rerun_global_market_state_linking",
    "rerun_global_link_root_cause_audit",
    "require_coverage_above_90_percent_before_context_linking",
]:
    print(f"STEP name={step}")

print("")
print("SUCCESS_CRITERIA")
print("criterion=coverage>=0.90")
print("criterion=no_snapshot<=10_percent")
print("criterion=NO_FEATURE_SNAPSHOT_reduced_materially")
print("criterion=NGN6_and_BRN6_not_systematically_missing")
print("criterion=runtime_changed=0")
print("criterion=execution_changed=0")

print("")
print("NEXT_STEPS")
print("next=GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_V1")
print("next=GLOBAL_LINK_REPAIR_IMPLEMENTATION_V1")

print("")
print("VERDICT=GLOBAL_LINK_REPAIR_PLAN_READY")
