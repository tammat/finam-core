#!/usr/bin/env python3

print("=== GOLD_20260624_ANOMALY_FILTER_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

print("\nTARGET_SYMBOLS")
print("GDU6@RTSX")
print("GLU6@RTSX")

print("\nHYPOTHESES")

print("H1=ONE_DAY_ANOMALY")
print("compare=2026-06-24 vs prior days")

print("H2=INTRADAY_BREAKPOINT")
print("compare=hour buckets")
print("focus=11,12,13 MSK")

print("H3=REGIME_SHIFT")
print("compare=prior expectancy vs 24h expectancy")

print("H4=ROLLOVER_OR_LIQUIDITY")
print("compare=volume/open_interest/contract_state if available")

print("\nEXPECTED_NEXT_AUDITS")

print("GOLD_20260624_DAY_EXCLUSION_AUDIT_V1")
print("GOLD_INTRADAY_BREAKPOINT_AUDIT_V1")
print("GOLD_REGIME_SHIFT_AUDIT_V1")

print("\nDECISION_MATRIX")

print("if remove_20260624 restores PF -> anomaly")
print("if degradation persists -> structural failure")
print("if only 11-13 MSK broken -> session filter candidate")
print("if all hours broken -> research_only")

print("\nVERDICT=GOLD_20260624_ANOMALY_FILTER_PLAN_READY")
