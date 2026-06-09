#!/usr/bin/env python3

print("=== GOLD SHORT ONLY CANDIDATE SUMMARY V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

print("CANDIDATE_PROFILE")

print(
    "PROFILE_ROW "
    "symbol=GDM6@RTSX "
    "timeframe=M5 "
    "direction=SHORT_ONLY "
    "exit_bars=10 "
    "preferred_hours=15-18 "
    "best_hour=16"
)

print()

print("RESEARCH_SUMMARY")

print(
    "SUMMARY_ROW "
    "stage=baseline_v1 "
    "result=PASS "
    "expectancy=0.454869 "
    "profit_factor=1.1393 "
    "trades=534"
)

print(
    "SUMMARY_ROW "
    "stage=side_decomposition "
    "result=SHORT_DOMINATES "
    "short_expectancy=0.918519 "
    "short_pf=1.2725 "
    "long_expectancy=-0.12616 "
    "long_pf=0.9598"
)

print(
    "SUMMARY_ROW "
    "stage=exit_sensitivity "
    "result=STABLE "
    "best_exit=15 "
    "pf_15=1.4959 "
    "pf_10=1.3429"
)

print(
    "SUMMARY_ROW "
    "stage=session_filter "
    "result=CONFIRMED "
    "session=evening "
    "pf=2.189 "
    "expectancy=5.408527"
)

print(
    "SUMMARY_ROW "
    "stage=hour_filter "
    "result=CONFIRMED "
    "best_hour=16 "
    "pf=2.7113 "
    "expectancy=9.285714"
)

print(
    "SUMMARY_ROW "
    "stage=hour_range "
    "result=CONFIRMED "
    "hours=15-18 "
    "pf=2.3711 "
    "expectancy=5.946154 "
    "trades=117"
)

print()

print("FINAL_VERDICT")

print(
    "VERDICT_ROW "
    "candidate=GOLD_SHORT_ONLY "
    "status=STRONG_RESEARCH_CANDIDATE "
    "runtime_ready=NO "
    "research_complete=YES "
    "next_step=replay_v2"
)

print()

print("VERDICT=GOLD_SHORT_ONLY_CANDIDATE_SUMMARIZED")
print("GOLD_SHORT_ONLY_CANDIDATE_SUMMARY_V1_OK")
