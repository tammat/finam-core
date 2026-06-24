#!/usr/bin/env python3

print("=== GOLD_FILTERED_RESEARCH_ONLY_DECISION_V1 ===")
print("mode=decision_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

print("\nDECISION_CONTEXT")
print("symbols=GDU6@RTSX,GLU6@RTSX")
print("edge_mode=FILTERED_BEFORE_19_MSK")
print("guard_status=shadow_only")
print("runtime_candidate=forbidden")

print("\nEVIDENCE")
print("day_exclusion_result=2026_06_24_ONE_DAY_ANOMALY")
print("intraday_breakpoint_found=0")
print("day_wide_anomaly=1")
print("exclude_11_13_msk_did_not_restore_pf=1")

print("\nRISK_FINDINGS")
print("recent_degradation=1")
print("recent_24h_negative=1")
print("runtime_ready=0")
print("execution_ready=0")
print("real_trading_ready=0")

print("\nFINAL_DECISION")
print("decision=KEEP_RESEARCH_ONLY")
print("reason=recent_degradation_and_unresolved_day_wide_anomaly")
print("required_before_runtime=stable_post_20260624_sample")
print("minimum_next_sample=50_completed_filtered_observations_per_symbol")
print("allowed_next_step=shadow_observation_only")

print("\nVERDICT=GOLD_FILTERED_RESEARCH_ONLY_DECISION_READY")
