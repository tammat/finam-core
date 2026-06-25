#!/usr/bin/env python3

print("=== UNIVERSE_BACKFILL_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("CURRENT_COVERAGE")
print("feature_rows_usable=69181")
print("closed_trades_usable=437")
print("strong_feature_sources=BRENT,NATURAL_GAS,USD_RUB,SBER,LKOH,PLZL")
print("weak_or_missing_sources=GOLD,SILVER,CNY_RUB,EUR_RUB,IMOEX,RTSI,SBERP,T,X5,ROSN,VTBR,SIBN,MAGN,GMKN,ALRS")

print("")
print("BACKFILL_PRIORITY_1")
for item in [
    "BRENT",
    "NATURAL_GAS",
    "USD_RUB",
    "SBER",
    "LKOH",
    "PLZL",
]:
    print(f"TARGET name={item} action=USE_EXISTING_FEATURES_AND_LINK_TRADES priority=1")

print("")
print("BACKFILL_PRIORITY_2")
for item in [
    "GOLD",
    "SILVER",
    "GAZP",
    "NVTK",
    "SBERP",
    "T",
    "X5",
]:
    print(f"TARGET name={item} action=REPAIR_OR_EXTEND_FEATURE_COVERAGE priority=2")

print("")
print("BACKFILL_PRIORITY_3")
for item in [
    "CNY_RUB",
    "EUR_RUB",
    "IMOEX",
    "RTSI",
    "ROSN",
    "VTBR",
    "SIBN",
    "MAGN",
    "GMKN",
    "ALRS",
]:
    print(f"TARGET name={item} action=SOURCE_DISCOVERY_REQUIRED priority=3")

print("")
print("BACKFILL_FLOW")
for step in [
    "build_universe_symbol_timeframe_windows",
    "select_priority_1_existing_feature_sources",
    "backfill_market_state_snapshots_for_priority_1",
    "backfill_context_states_for_available_contexts",
    "link_closed_trades_to_market_states",
    "link_market_context_to_trade_states",
    "run_global_context_scorecard",
    "write_candidates_to_knowledge_base",
]:
    print(f"STEP name={step}")

print("")
print("SAFETY_GUARDS")
for guard in [
    "research_only",
    "postgres_only",
    "no_sqlite",
    "no_runtime_write",
    "no_execution_write",
    "no_orders",
    "no_micro_live_promotion",
    "idempotent_backfill_required",
]:
    print(f"GUARD name={guard}")

print("")
print("NEXT_STEPS")
print("next=UNIVERSE_BACKFILL_IMPLEMENTATION_V1")
print("next=GLOBAL_EDGE_DISCOVERY_V1")

print("")
print("VERDICT=UNIVERSE_BACKFILL_PLAN_READY")
