#!/usr/bin/env python3

print("=== GOLD REPLAY V2 FINAL CANDIDATE SUMMARY ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

print("FINAL_PROFILE")

print(
    "PROFILE_ROW "
    "symbol=GDM6@RTSX "
    "timeframe=M5 "
    "direction=SHORT_ONLY "
    "hours_msk=15,16,17,18 "
    "exit_bars=10 "
    "status=STRONG_REPLAY_CANDIDATE"
)

print()

print("RESEARCH_TIMELINE")

print(
    "TIMELINE_ROW "
    "stage=baseline "
    "result=PASS "
    "trades=534 "
    "expectancy=0.454869 "
    "profit_factor=1.1393"
)

print(
    "TIMELINE_ROW "
    "stage=side_decomposition "
    "result=SHORT_DOMINATES "
    "short_pf=1.2725 "
    "long_pf=0.9598"
)

print(
    "TIMELINE_ROW "
    "stage=exit_sensitivity "
    "result=STABLE "
    "best_exit=15 "
    "pf_15=1.4959 "
    "pf_10=1.3429"
)

print(
    "TIMELINE_ROW "
    "stage=session_filter "
    "result=CONFIRMED "
    "session=evening "
    "pf=2.189"
)

print(
    "TIMELINE_ROW "
    "stage=hour_filter "
    "result=CONFIRMED "
    "best_hour=16 "
    "pf=2.7113"
)

print(
    "TIMELINE_ROW "
    "stage=replay_v2 "
    "result=STRONG_CANDIDATE "
    "trades=140 "
    "expectancy=8.375 "
    "pf=3.3108"
)

print()

print("RANGE_COMPARISON")

print(
    "RANGE_ROW "
    "range=HOUR_16 "
    "trades=43 "
    "expectancy=9.388372 "
    "pf=2.7714 "
    "max_drawdown=-179.7"
)

print(
    "RANGE_ROW "
    "range=HOURS_15_18 "
    "trades=140 "
    "expectancy=8.375 "
    "pf=3.3108 "
    "max_drawdown=-245.1 "
    "best=yes"
)

print(
    "RANGE_ROW "
    "range=EVENING_14_18 "
    "trades=152 "
    "expectancy=7.726974 "
    "pf=3.0015 "
    "max_drawdown=-324.5"
)

print(
    "RANGE_ROW "
    "range=WIDE_13_18 "
    "trades=167 "
    "expectancy=7.840719 "
    "pf=3.1922 "
    "max_drawdown=-333.2"
)

print()

print("FINAL_VERDICT")

print(
    "VERDICT_ROW "
    "candidate=GOLD_SHORT_ONLY "
    "symbol=GDM6@RTSX "
    "timeframe=M5 "
    "hours=15-18 "
    "exit_bars=10 "
    "status=STRONG_REPLAY_CANDIDATE "
    "runtime_ready=NO "
    "research_complete=YES "
    "next_step=runtime_shadow_validation"
)

print()

print("VERDICT=GOLD_REPLAY_V2_FINAL_CANDIDATE_SUMMARIZED")
print("GOLD_REPLAY_V2_FINAL_CANDIDATE_SUMMARY_OK")
