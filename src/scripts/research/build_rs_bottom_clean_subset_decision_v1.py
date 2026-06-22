#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("=== RS_BOTTOM_CLEAN_SUBSET_DECISION_V1 ===")
print("mode=research_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("telegram_send=0")

print("DECISION_ROW key=RS_BOTTOM_CURRENT_VERSION_REJECTED value=1 reason=full_forward_set_real_pf_below_1")
print("DECISION_ROW key=RS_BOTTOM_CLEAN_SUBSET_RESEARCH_CANDIDATE value=1 reason=clean_subset_real_pf_2_651425_completed_49")
print("DECISION_ROW key=NG_EXCLUDED value=1 reason=ng_completed_17_success_0_failure_17")
print("DECISION_ROW key=COMPRESSION_RANGE_EXCLUDED value=1 reason=compression_range_real_pf_0_433897")
print("DECISION_ROW key=MSK_12H_EXCLUDED value=1 reason=msk_12h_completed_42_success_0_failure_42")
print("DECISION_ROW key=REVERSAL_UP_CLOSE_ONLY value=1 reason=clean_subset_keeps_reversal_up_close")
print("DECISION_ROW key=BRN6_PRIMARY_RESEARCH_CANDIDATE value=1 reason=brn6_real_pf_5_567864_completed_15")
print("DECISION_ROW key=REAL_TRADING_ALLOWED value=0 reason=research_only_forward_sample_not_enough_for_live")

print("SUMMARY full_version=REJECTED clean_subset=RESEARCH_CANDIDATE real_trading=DISABLED")
print("VERDICT=RS_BOTTOM_CLEAN_SUBSET_DECISION_READY")
print("TEST_RS_BOTTOM_CLEAN_SUBSET_DECISION_V1_OK")
