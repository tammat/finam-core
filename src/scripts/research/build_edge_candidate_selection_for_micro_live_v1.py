#!/usr/bin/env python3

# ==========================================================
# EDGE_CANDIDATE_SELECTION_FOR_MICRO_LIVE_V1
#
# Отбор edge-кандидата для Micro Live.
#
# ВАЖНО:
# - это НЕ включение реальной торговли;
# - реальные заявки не отправляются;
# - Runtime не изменяется;
# - Execution не изменяется;
# - при отсутствии подтвержденного edge кандидат не выбирается.
# ==========================================================

print("=== EDGE_CANDIDATE_SELECTION_FOR_MICRO_LIVE_V1 ===")
print("mode=selection_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

selection_criteria = [
    "state_edge_scorecard_positive",
    "expectancy_positive_after_commission",
    "profit_factor_above_threshold",
    "sample_size_guard_passed",
    "bias_guard_passed",
    "commission_drag_not_dominant",
    "shadow_validation_ready",
    "paper_validation_ready",
    "risk_fit_possible",
    "execution_fit_possible",
]

print("\nSELECTION_CRITERIA")
for item in selection_criteria:
    print(f"CRITERION name={item}")

candidate_sources = [
    "research.state_edge_scorecards_v1",
    "research.strategy_state_matrix_v1",
    "research.research_decisions_v1",
    "clean_runtime_or_paper_trade_source_class",
]

print("\nCANDIDATE_SOURCES")
for item in candidate_sources:
    print(f"SOURCE name={item}")

blocking_reasons = [
    "NO_CONFIRMED_EDGE_CANDIDATE_YET",
    "NO_VALIDATED_STATE_EDGE_SCORECARD_YET",
    "NO_SHADOW_VALIDATION_YET",
    "NO_PAPER_VALIDATION_YET",
    "MICRO_LIVE_GATE_STILL_BLOCKED",
]

print("\nCURRENT_BLOCKERS")
for item in blocking_reasons:
    print(f"BLOCKER name={item}")

print("\nSELECTION_RESULT")
print("eligible_candidates=0")
print("selected_candidate=NONE")
print("micro_live_allowed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("\nDESIGN_RULES")
print("rule=no_candidate_without_positive_edge")
print("rule=no_candidate_without_commission_adjusted_expectancy")
print("rule=no_candidate_without_bias_guard")
print("rule=no_candidate_without_shadow_and_paper_validation")
print("rule=selection_script_cannot_enable_runtime")
print("rule=no_runtime_execution_changes")

print("\nNEXT_STEPS")
print("next=EDGE_CANDIDATE_DISCOVERY_FROM_EXISTING_SCORECARDS_V1")
print("next=EDGE_CANDIDATE_VALIDATION_FOR_MICRO_LIVE_V1")

print("\nVERDICT=EDGE_CANDIDATE_SELECTION_NO_ELIGIBLE_CANDIDATE_NOT_ENABLED")
