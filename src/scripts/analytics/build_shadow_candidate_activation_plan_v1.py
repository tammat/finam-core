#!/usr/bin/env python3
from __future__ import annotations

print("=== SHADOW CANDIDATE ACTIVATION PLAN V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

print("CANDIDATE_ROWS")
print("CANDIDATE_ROW rank=1 symbol=USDRUBF@RTSX root=USD timeframe=M5 strategy=usd_shadow_watch_v1 table=runtime_shadow_candidate_signals_v1 mode=shadow_only runtime_allow=0 min_signals=50 min_closed_shadow=30 review=scorecard_v1")
print("CANDIDATE_ROW rank=2 symbol=LKOH@MISX root=LKOH timeframe=M5 strategy=lkoh_shadow_watch_v1 table=runtime_shadow_candidate_signals_v1 mode=shadow_only runtime_allow=0 min_signals=50 min_closed_shadow=30 review=scorecard_v1")
print()

print("QUALITY_RULES")
print("RULE_ROW name=no_runtime_execution value=required")
print("RULE_ROW name=min_signals value=50")
print("RULE_ROW name=min_closed_shadow value=30")
print("RULE_ROW name=profit_factor_threshold value=1.2")
print("RULE_ROW name=expectancy_threshold value=positive")
print("RULE_ROW name=recent_decay value=must_not_be_confirmed")
print("RULE_ROW name=walkforward value=must_not_be_unstable")
print()

print("DECISION_RULES")
print("DECISION_ROW result=PROMOTE_TO_RUNTIME condition=pf_ge_1_2_and_expectancy_positive_and_no_decay")
print("DECISION_ROW result=WATCH_ONLY condition=positive_but_mixed_or_insufficient_sample")
print("DECISION_ROW result=REJECT condition=negative_expectancy_or_decay_confirmed")
print()

print("SUMMARY_ROW selected=2 runtime_allow=0 shadow_only=1")
print("VERDICT=SHADOW_CANDIDATE_ACTIVATION_PLAN_RECORDED")
print("SHADOW_CANDIDATE_ACTIVATION_PLAN_V1_OK")
