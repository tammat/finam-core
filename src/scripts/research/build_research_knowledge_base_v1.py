#!/usr/bin/env python3

print("=== RESEARCH_KNOWLEDGE_BASE_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("PURPOSE")
print("purpose=centralize_research_knowledge")
print("purpose=preserve_candidate_decisions")
print("purpose=prevent_retesting_rejected_hypotheses")
print("purpose=track_edge_lifecycle")

print("")
print("KNOWLEDGE_OBJECTS")
for item in [
    "edge_candidate",
    "market_state_context_candidate",
    "rejected_hypothesis",
    "validated_pattern",
    "data_quality_issue",
    "commission_slippage_issue",
    "runtime_promotion_decision",
    "micro_live_decision",
]:
    print(f"object={item}")

print("")
print("CANDIDATE_LIFECYCLE")
for status in [
    "DISCOVERED",
    "UNDER_RESEARCH",
    "REJECTED",
    "ARCHIVED",
    "PROMOTED_TO_SHADOW",
    "PROMOTED_TO_MICRO_LIVE",
    "PROMOTED_TO_RUNTIME",
    "DEPRECATED",
]:
    print(f"status={status}")

print("")
print("REJECTION_REASONS")
for reason in [
    "ROBUSTNESS_WEAK",
    "INSUFFICIENT_SAMPLE",
    "NEGATIVE_EXPECTANCY",
    "LOW_PROFIT_FACTOR",
    "HIGH_DRAWDOWN",
    "COMMISSION_DOMINATES",
    "SLIPPAGE_DOMINATES",
    "MARKET_REGIME_DEPENDENT",
    "DUPLICATE_OF_EXISTING",
    "DATA_QUALITY",
]:
    print(f"reason={reason}")

print("")
print("FIRST_KNOWN_CANDIDATE")
print("candidate_id=MSC-000001")
print("instrument_signature=MS-A51761DAAE2F")
print("fx_signature=MS-B3C22849CB56")
print("energy_signature=MS-A51761DAAE2F")
print("trades=77")
print("net_pnl=147.290019")
print("expectancy=1.912857")
print("profit_factor=1.942233")
print("robustness=WEAK")
print("status=REJECTED")
print("status_reason=ROBUSTNESS_WEAK")
print("rejection_detail=72_of_77_trades_clustered_on_one_day")

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
print("DESIGN_RULES")
for rule in [
    "candidate_id_is_immutable",
    "signatures_are_versioned",
    "decisions_are_append_only",
    "rejections_are_preserved",
    "promotion_requires_validation_chain",
    "knowledge_base_is_research_only",
    "no_runtime_execution_changes",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=RESEARCH_KNOWLEDGE_BASE_SCHEMA_PLAN_V1")
print("next=MARKET_STATE_CONTEXT_CANDIDATE_REGISTRY_V1")

print("")
print("VERDICT=RESEARCH_KNOWLEDGE_BASE_PLAN_READY")
