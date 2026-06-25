#!/usr/bin/env python3

# ==========================================================
# RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_V1
#
# План Strategy Recommendation Engine.
#
# Назначение:
# - сопоставлять подтвержденные состояния рынка с подходящими стратегиями;
# - формировать исследовательскую рекомендацию;
# - не менять Runtime и Execution напрямую.
#
# ВАЖНО:
# - только plan_only;
# - БД не изменяется;
# - Runtime не изменяется;
# - Execution не изменяется;
# - реальные заявки не отправляются.
# ==========================================================

print("=== RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

stages = [
    ("CandidateStateSelector", 1, "Выбирает только состояния с подтвержденным edge."),
    ("StrategyUniverseSelector", 2, "Определяет допустимые стратегии для класса актива и таймфрейма."),
    ("StrategyStateMatcher", 3, "Сопоставляет стратегию с состоянием рынка."),
    ("RiskFitEvaluator", 4, "Проверяет совместимость стратегии с риск-ограничениями."),
    ("ExecutionFitEvaluator", 5, "Проверяет реализуемость стратегии с учетом комиссий, ликвидности и проскальзывания."),
    ("RecommendationScorer", 6, "Формирует итоговый score рекомендации."),
    ("PromotionGate", 7, "Определяет следующий допустимый статус: WATCH, RESEARCH, SHADOW, PAPER, MICRO_LIVE_CANDIDATE."),
    ("DecisionBuilder", 8, "Формирует исследовательское решение и основание рекомендации."),
]

print("\nRECOMMENDATION_STAGES")
for code, order, description in stages:
    print(f"RECOMMENDATION_STAGE order={order} code={code} description_ru={description}")

inputs = [
    "state_edge_scorecard",
    "state_edge_candidate",
    "state_robustness_report",
    "state_bias_guard_report",
    "strategy_catalog",
    "strategy_state_matrix",
    "risk_limits",
    "execution_constraints",
]

print("\nENGINE_INPUTS")
for value in inputs:
    print(f"ENGINE_INPUT name={value}")

outputs = [
    "strategy_recommendation",
    "recommended_strategy",
    "recommended_market_state",
    "recommendation_score",
    "risk_fit_report",
    "execution_fit_report",
    "promotion_gate_decision",
    "research_decision",
]

print("\nENGINE_OUTPUTS")
for value in outputs:
    print(f"ENGINE_OUTPUT name={value}")

metrics = [
    "state_expectancy",
    "state_profit_factor",
    "strategy_expectancy_in_state",
    "strategy_profit_factor_in_state",
    "net_pnl_after_commission",
    "commission_drag",
    "sample_size",
    "robustness_score",
    "bias_risk_score",
    "risk_fit_score",
    "execution_fit_score",
    "recommendation_score",
]

print("\nRECOMMENDATION_METRICS")
for value in metrics:
    print(f"RECOMMENDATION_METRIC name={value}")

promotion_statuses = [
    "REJECTED",
    "WATCH_MORE_DATA",
    "RESEARCH_CANDIDATE",
    "SHADOW_CANDIDATE",
    "PAPER_CANDIDATE",
    "MICRO_LIVE_CANDIDATE",
]

print("\nPROMOTION_STATUSES")
for status in promotion_statuses:
    print(f"PROMOTION_STATUS code={status}")

contracts = [
    "engine_reads_edge_candidates_only",
    "engine_reads_strategy_catalog",
    "engine_does_not_change_runtime",
    "engine_does_not_change_execution",
    "engine_never_sends_orders",
    "engine_never_enables_strategy_directly",
    "engine_outputs_research_recommendation_only",
    "promotion_requires_separate_validation",
    "micro_live_requires_manual_or_governed_approval",
]

print("\nENGINE_CONTRACTS")
for contract in contracts:
    print(f"contract={contract}")

print("\nDESIGN_RULES")
rules = [
    "strategy_recommendation_engine_is_research_only",
    "state_edge_candidate_required_before_strategy_recommendation",
    "strategy_must_match_asset_class",
    "strategy_must_match_timeframe",
    "strategy_must_have_state_matrix_row",
    "risk_fit_required",
    "execution_fit_required",
    "commission_drag_check_required",
    "bias_guard_report_required",
    "promotion_gate_cannot_enable_runtime",
    "micro_live_candidate_requires_separate_preparation",
    "no_runtime_execution_changes",
]
for rule in rules:
    print(f"rule={rule}")

print("\nFILE_STRUCTURE")
print("file=src/scripts/research/build_research_strategy_recommendation_engine_plan_v1.py")
print("file=scripts/test_research_strategy_recommendation_engine_plan_v1.sh")

print("\nNEXT_STEPS")
print("next=MICRO_LIVE_PREPARATION_V1")

print("\nVERDICT=RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_READY")
