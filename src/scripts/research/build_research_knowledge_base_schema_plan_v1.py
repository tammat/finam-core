#!/usr/bin/env python3

print("=== RESEARCH_KNOWLEDGE_BASE_SCHEMA_PLAN_V1 ===")
print("mode=schema_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("TARGET_TABLES")
for table in [
    "research.research_candidates_v1",
    "research.research_candidate_decisions_v1",
    "research.research_hypotheses_v1",
    "research.research_knowledge_events_v1",
]:
    print(f"table={table}")

print("")
print("CANDIDATE_COLUMNS")
for col in [
    "candidate_id",
    "candidate_version",
    "candidate_type",
    "instrument_signature",
    "fx_signature",
    "energy_signature",
    "session_signature",
    "symbol",
    "strategy",
    "timeframe",
    "trade_count",
    "winrate",
    "expectancy",
    "profit_factor",
    "net_pnl",
    "commission",
    "max_drawdown",
    "validation_level",
    "status",
    "status_reason",
    "discovered_at",
    "last_validation_at",
    "created_by_script",
    "payload",
    "created_at",
]:
    print(f"column={col}")

print("")
print("DECISION_COLUMNS")
for col in [
    "decision_id",
    "candidate_id",
    "decision_ts",
    "old_status",
    "new_status",
    "decision_reason",
    "decision_detail",
    "decided_by_script",
    "payload",
    "created_at",
]:
    print(f"column={col}")

print("")
print("DESIGN_RULES")
for rule in [
    "candidate_id_is_immutable",
    "candidate_decisions_are_append_only",
    "candidate_status_current_in_candidates_table",
    "candidate_history_in_decisions_table",
    "hypotheses_are_separate_from_candidates",
    "knowledge_events_capture_all_major_research_decisions",
    "research_only",
    "no_runtime_execution_changes",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=RESEARCH_KNOWLEDGE_BASE_SCHEMA_DRY_RUN_V1")

print("")
print("VERDICT=RESEARCH_KNOWLEDGE_BASE_SCHEMA_PLAN_READY")
