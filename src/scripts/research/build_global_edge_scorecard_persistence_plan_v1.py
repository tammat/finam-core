#!/usr/bin/env python3

print("=== GLOBAL_EDGE_SCORECARD_PERSISTENCE_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("PROBLEM")
print("global_edge_discovery_rows_are_stdout_only=1")
print("scorecard_not_persisted=1")
print("candidate_reproducibility_weak=1")
print("edge_evolution_tracking_missing=1")

print("")
print("INPUT_RESULT")
print("source_checkpoint=checkpoint_global_edge_discovery_v1")
print("rows_total=231")
print("positive_rows=65")
print("research_candidates=1")
print("rejected_small_sample=64")
print("micro_live_candidates=0")

print("")
print("TARGET_TABLES")
print("table=research.analytics_global_edge_scorecard_v1")
print("table=research.analytics_global_edge_scorecard_runs_v1")

print("")
print("RUN_COLUMNS")
for col in [
    "run_id",
    "run_ts",
    "source_script",
    "source_checkpoint",
    "rows_total",
    "positive_rows",
    "research_candidates",
    "micro_live_candidates",
    "research_version",
    "payload",
    "created_at",
]:
    print(f"column={col}")

print("")
print("SCORECARD_COLUMNS")
for col in [
    "id",
    "run_id",
    "symbol",
    "strategy",
    "timeframe",
    "instrument_signature",
    "fx_signature",
    "energy_signature",
    "trades",
    "wins",
    "losses",
    "winrate",
    "net_pnl",
    "expectancy",
    "profit_factor",
    "first_trade",
    "last_trade",
    "status",
    "reason",
    "payload",
    "created_at",
]:
    print(f"column={col}")

print("")
print("DESIGN_RULES")
for rule in [
    "scorecard_runs_are_append_only",
    "scorecard_rows_are_versioned_by_run_id",
    "stdout_is_not_source_of_truth",
    "research_candidates_can_be_seeded_from_persisted_scorecard",
    "no_micro_live_promotion_from_persistence",
    "no_runtime_execution_changes",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_DRY_RUN_V1")
print("next=GLOBAL_EDGE_SCORECARD_PERSISTENCE_APPLY_V1")
print("next=GLOBAL_EDGE_CANDIDATE_AUDIT_V1")

print("")
print("VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_PLAN_READY")
