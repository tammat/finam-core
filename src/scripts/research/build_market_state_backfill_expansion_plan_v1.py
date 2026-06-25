#!/usr/bin/env python3

print("=== MARKET_STATE_BACKFILL_EXPANSION_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("PROBLEM")
print("current_trade_source=public.trade_outcomes")
print("current_trades=44")
print("current_symbol=BRN6@RTSX")
print("current_period=2026-05-18..2026-05-27")
print("sample_status=INSUFFICIENT_FOR_EDGE")

print("")
print("DECISION")
print("decision=SEARCH_BROADER_HISTORICAL_TRADE_SOURCES")
print("reason=44_trades_is_not_enough_for_market_state_edge")
print("reason=need_300_plus_linked_trades_before_research_candidate")

print("")
print("CANDIDATE_SOURCES")
sources = [
    "public.trade_outcomes",
    "public.closed_trade_chains_v3",
    "public.v_trades_pnl_paired_grafana",
    "public.virtual_signal_trades",
    "public.analytics_intrabar_trade_quality",
    "public.strategy_exit_alpha_bar_replay",
]
for source in sources:
    print(f"SOURCE name={source}")

print("")
print("NEXT_ACTIONS")
actions = [
    "audit_all_trade_sources_row_counts",
    "audit_symbol_timeframe_date_ranges",
    "select_canonical_historical_trade_source",
    "backfill_market_states_for_selected_trade_windows",
    "rerun_trade_linking",
    "rerun_pnl_scorecard",
]
for action in actions:
    print(f"ACTION name={action}")

print("")
print("NEXT_STEPS")
print("next=HISTORICAL_TRADE_SOURCE_AUDIT_V1")

print("")
print("VERDICT=MARKET_STATE_BACKFILL_EXPANSION_PLAN_READY")
