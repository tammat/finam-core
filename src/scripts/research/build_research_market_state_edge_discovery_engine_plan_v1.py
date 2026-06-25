#!/usr/bin/env python3

# ==========================================================
# RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_V1
#
# План Edge Discovery Engine для состояний рынка.
#
# Назначение:
# - искать статистически подтвержденный edge по Market State Snapshot;
# - оценивать состояния рынка, а не подгонять стратегии;
# - готовить кандидатов для Strategy Recommendation и Micro Live.
#
# ВАЖНО:
# - только plan_only;
# - БД не изменяется;
# - Runtime не изменяется;
# - Execution не изменяется;
# - реальные заявки не отправляются.
# ==========================================================

print("=== RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

stages = [
    ("DatasetSelector", 1, "Выбирает только допустимые исследовательские данные и чистые источники сделок."),
    ("StateTradeLinker", 2, "Связывает сделки с entry/exit Market State Snapshot."),
    ("StateGrouper", 3, "Группирует сделки по canonical_signature и compact_signature."),
    ("MetricCalculator", 4, "Считает expectancy, profit_factor, winrate, net_pnl, commission_drag, MAE, MFE."),
    ("RobustnessChecker", 5, "Проверяет устойчивость edge по периодам, инструментам, сессиям и выборкам."),
    ("BiasGuard", 6, "Проверяет риск переобучения, data snooping и малой выборки."),
    ("CandidateSelector", 7, "Отбирает состояния-кандидаты для дальнейшей проверки."),
    ("DecisionBuilder", 8, "Формирует исследовательский вердикт: REJECTED, WATCH, RESEARCH_CANDIDATE, MICRO_LIVE_CANDIDATE."),
]

print("\nEDGE_DISCOVERY_STAGES")
for code, order, description in stages:
    print(f"EDGE_STAGE order={order} code={code} description_ru={description}")

inputs = [
    "research.market_state_snapshots_v1",
    "research.market_state_snapshot_values_v1",
    "research.trade_state_snapshots_v1",
    "research.trade_facts_or_clean_trade_source",
    "market_state_canonical_signature",
    "market_state_compact_signature",
]

print("\nENGINE_INPUTS")
for value in inputs:
    print(f"ENGINE_INPUT name={value}")

outputs = [
    "state_edge_scorecard",
    "state_edge_candidate",
    "state_edge_rejection_reason",
    "state_robustness_report",
    "state_bias_guard_report",
    "research_decision",
]

print("\nENGINE_OUTPUTS")
for value in outputs:
    print(f"ENGINE_OUTPUT name={value}")

metrics = [
    "trades",
    "closed_cycles",
    "wins",
    "losses",
    "winrate",
    "gross_pnl",
    "commission",
    "net_pnl",
    "profit_factor",
    "expectancy",
    "avg_net_per_trade",
    "mae",
    "mfe",
    "holding_time",
    "commission_drag",
    "sample_days",
    "symbols_count",
]

print("\nEDGE_METRICS")
for value in metrics:
    print(f"EDGE_METRIC name={value}")

candidate_rules = [
    "min_closed_cycles_required",
    "positive_expectancy_required",
    "profit_factor_above_threshold_required",
    "net_pnl_positive_after_commission_required",
    "commission_drag_not_dominant",
    "multi_day_or_walk_forward_confirmation_required",
    "sample_size_guard_required",
    "no_single_day_overfit",
    "no_single_symbol_overfit_unless_explicit_scope",
]

print("\nCANDIDATE_RULES")
for rule in candidate_rules:
    print(f"CANDIDATE_RULE name={rule}")

verdicts = [
    "REJECTED_NEGATIVE_EDGE",
    "REJECTED_INSUFFICIENT_DATA",
    "REJECTED_FEE_DRAG",
    "REJECTED_OVERFIT_RISK",
    "WATCH_MORE_DATA",
    "RESEARCH_CANDIDATE",
    "MICRO_LIVE_CANDIDATE",
]

print("\nEDGE_VERDICTS")
for verdict in verdicts:
    print(f"EDGE_VERDICT code={verdict}")

contracts = [
    "engine_reads_market_states_and_trade_results",
    "engine_does_not_change_market_state_snapshots",
    "engine_does_not_change_runtime",
    "engine_does_not_change_execution",
    "engine_never_sends_orders",
    "engine_never_promotes_to_runtime_directly",
    "engine_outputs_research_decision_only",
    "edge_is_calculated_after_market_state_generation",
    "edge_discovery_is_money_first",
]

print("\nENGINE_CONTRACTS")
for contract in contracts:
    print(f"contract={contract}")

print("\nDESIGN_RULES")
rules = [
    "edge_discovery_engine_is_research_only",
    "market_state_engine_must_run_before_edge_discovery",
    "trade_source_class_filter_required",
    "clean_runtime_or_paper_layer_must_be_separated",
    "historical_replay_must_be_separated",
    "legacy_backfill_must_be_excluded_from_clean_edge",
    "scorecard_must_include_commission",
    "scorecard_must_include_sample_size",
    "scorecard_must_include_rejection_reason",
    "micro_live_candidate_requires_separate_validation",
    "no_runtime_execution_changes",
]
for rule in rules:
    print(f"rule={rule}")

print("\nFILE_STRUCTURE")
print("file=src/scripts/research/build_research_market_state_edge_discovery_engine_plan_v1.py")
print("file=scripts/test_research_market_state_edge_discovery_engine_plan_v1.sh")

print("\nNEXT_STEPS")
print("next=RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_V1")
print("next=MICRO_LIVE_PREPARATION_V1")

print("\nVERDICT=RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_READY")
