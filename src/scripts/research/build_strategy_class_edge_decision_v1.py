#!/usr/bin/env python3

print("=== STRATEGY_CLASS_EDGE_DECISION_V1 ===")
print("mode=decision_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

print("\nSOURCE")
print("source_table=analytics_rs_bottom_runtime_dry_run_v1")
print("checkpoint=checkpoint_strategy_class_discovery_audit_v2")

print("\nCLASS_DECISIONS")
print("CLASS_DECISION strategy_class=COMPRESSION_EXPANSION completed=102 pf=1.0397 expectancy=0.011128 net_pnl_estimate=-0.904956 decision=WATCH_ONLY reason=fee_drag_kills_edge")
print("CLASS_DECISION strategy_class=UNKNOWN completed=31 pf=0.0304 expectancy=-0.586599 net_pnl_estimate=-18.804559 decision=REJECT reason=negative_expectancy_and_low_pf")

print("\nFINAL_DECISION")
print("runtime_candidate=NONE")
print("promote_to_runtime=0")
print("promote_to_research_candidate=0")
print("watch_only=COMPRESSION_EXPANSION")
print("reject=UNKNOWN")
print("main_problem=average_edge_too_small_relative_to_fee_drag")

print("\nNEXT_RESEARCH_DIRECTION")
print("1=improve_exit_or_take_profit_to_increase_avg_win")
print("2=reduce_signal_frequency_by_quality_filter")
print("3=test_non_breakout_strategy_classes")
print("4=build_signal_funnel_from_signals_table")

print("\nVERDICT=STRATEGY_CLASS_EDGE_DECISION_READY")
