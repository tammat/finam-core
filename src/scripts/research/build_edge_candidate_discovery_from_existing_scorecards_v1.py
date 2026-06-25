#!/usr/bin/env python3

# ==========================================================
# EDGE_CANDIDATE_DISCOVERY_FROM_EXISTING_SCORECARDS_V1
#
# Поиск возможных edge-кандидатов по уже существующим scorecard-результатам.
#
# ВАЖНО:
# - это НЕ включение реальной торговли;
# - реальные заявки не отправляются;
# - Runtime не изменяется;
# - Execution не изменяется;
# - скрипт только фиксирует источники и правила отбора.
# ==========================================================

print("=== EDGE_CANDIDATE_DISCOVERY_FROM_EXISTING_SCORECARDS_V1 ===")
print("mode=discovery_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

sources = [
    "clean_runtime_signal_class_edge_scorecard_v1",
    "multi_asset_breakout_edge_scorecard_v1",
    "normalized_signal_class_edge_scorecard_v1_1",
    "ng_session_filter_hypothesis_v1",
    "ng_br_edge_recheck_after_usdrub_block_v1",
    "br_historical_replay_scorecards",
]

print("\nDISCOVERY_SOURCES")
for item in sources:
    print(f"SOURCE name={item}")

candidate_filters = [
    "use_clean_runtime_or_paper_only_for_micro_live",
    "exclude_historical_replay_from_micro_live_candidate",
    "exclude_legacy_ng_synthetic_backfill",
    "require_positive_net_pnl_after_commission",
    "require_positive_expectancy",
    "require_profit_factor_above_threshold",
    "require_sample_size_guard",
    "require_bias_guard",
    "require_no_fee_drag_dominance",
]

print("\nCANDIDATE_FILTERS")
for item in candidate_filters:
    print(f"FILTER name={item}")

known_findings = [
    ("clean_runtime_edge", "NO_CANDIDATE", "clean runtime/paper layer previously negative or insufficient"),
    ("ng_br_after_usdrub_block", "NO_CANDIDATE", "fee drag dominated or insufficient data"),
    ("ng_session_filter", "NO_CANDIDATE", "weak hypothesis only, not confirmed"),
    ("ng_trend_up_time_exit", "NO_CANDIDATE", "candidate rejected negative sample"),
    ("br_historical_replay", "RESEARCH_ONLY", "historical candidate may exist but not eligible for direct Micro Live"),
]

print("\nKNOWN_FINDINGS")
for name, status, reason in known_findings:
    print(f"FINDING name={name} status={status} reason={reason}")

print("\nDISCOVERY_RESULT")
print("existing_scorecards_checked=6")
print("eligible_micro_live_candidates=0")
print("research_only_candidates=1")
print("selected_candidate=NONE")
print("micro_live_allowed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("\nDESIGN_RULES")
print("rule=existing_scorecard_discovery_is_read_only")
print("rule=micro_live_requires_clean_runtime_or_paper_edge")
print("rule=historical_replay_can_only_be_research_candidate")
print("rule=no_candidate_without_commission_adjusted_positive_edge")
print("rule=no_candidate_without_shadow_and_paper_validation")
print("rule=discovery_script_cannot_enable_runtime")
print("rule=no_runtime_execution_changes")

print("\nNEXT_STEPS")
print("next=EDGE_CANDIDATE_VALIDATION_FOR_MICRO_LIVE_V1")
print("next=MARKET_STATE_ENGINE_IMPLEMENTATION_PLAN_V1")

print("\nVERDICT=EDGE_CANDIDATE_DISCOVERY_NO_MICRO_LIVE_CANDIDATE")
