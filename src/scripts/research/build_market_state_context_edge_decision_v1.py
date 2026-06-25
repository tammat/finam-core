#!/usr/bin/env python3

print("=== MARKET_STATE_CONTEXT_EDGE_DECISION_V1 ===")
print("mode=decision_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("INPUT_SUMMARY")
print("context_links=482")
print("scorecard_rows_total=59")
print("positive_rows=19")
print("research_candidates=1")
print("micro_live_candidates=0")

print("")
print("TOP_RESEARCH_CANDIDATE")
print("instrument_signature=MS-A51761DAAE2F")
print("fx_signature=MS-B3C22849CB56")
print("energy_signature=MS-A51761DAAE2F")
print("trades=77")
print("wins=36")
print("losses=41")
print("winrate=0.4675")
print("net_pnl=147.290019")
print("expectancy=1.912857")
print("profit_factor=1.942233")
print("first_trade=2026-05-05T13:14:27.802519+00:00")
print("last_trade=2026-05-11T09:54:29.894676+00:00")
print("status=RESEARCH_CANDIDATE")

print("")
print("DECISION")
print("decision=DO_NOT_PROMOTE_TO_MICRO_LIVE")
print("decision=CONTINUE_RESEARCH_VALIDATION")
print("reason=single_candidate_only")
print("reason=needs_out_of_sample_validation")
print("reason=needs_commission_and_slippage_recheck")
print("reason=needs_day_split_robustness_check")
print("reason=needs_strategy_and_symbol_breakdown")

print("")
print("REQUIRED_VALIDATION")
for item in [
    "candidate_trade_list_audit",
    "daily_pnl_split",
    "symbol_strategy_breakdown",
    "commission_slippage_recheck",
    "out_of_sample_forward_validation",
    "context_signature_explanation",
]:
    print(f"validation={item}")

print("")
print("NEXT_STEPS")
print("next=MARKET_STATE_CONTEXT_CANDIDATE_AUDIT_V1")
print("next=MARKET_STATE_CONTEXT_ROBUSTNESS_CHECK_V1")

print("")
print("VERDICT=MARKET_STATE_CONTEXT_EDGE_DECISION_RESEARCH_CANDIDATE_NOT_MICRO_LIVE")
