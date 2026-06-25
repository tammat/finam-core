#!/usr/bin/env python3

print("=== RESEARCH_UNIVERSE_V1 ===")
print("mode=constitution_plan")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("UNIVERSE_SCOPE")
print("scope=research_baseline_universe")
print("status=APPROVED_AFTER_ARCHITECTURE_FREEZE")
print("principle=new_instruments_require_architectural_decision")

print("")
print("FUTURES_PRIORITY_1")
for item in [
    ("BRENT", "BR", "energy_futures"),
    ("NATURAL_GAS", "NG", "energy_futures"),
    ("GOLD", "GD", "metals_futures"),
    ("SILVER", "SV", "metals_futures"),
    ("USD_RUB", "USDRUBF", "fx_futures"),
    ("CNY_RUB", "CNYRUBF", "fx_futures"),
    ("EUR_RUB", "EURRUBF", "fx_futures"),
]:
    print(f"INSTRUMENT class=FUTURES name={item[0]} symbol_family={item[1]} asset_group={item[2]} priority=1")

print("")
print("EQUITY_PRIORITY_2")
for ticker in [
    "SBER", "SBERP", "LKOH", "GAZP", "NVTK", "T", "X5",
    "PLZL", "ROSN", "VTBR", "SIBN", "MAGN", "GMKN", "ALRS",
]:
    print(f"INSTRUMENT class=EQUITY ticker={ticker} exchange=MISX priority=2")

print("")
print("MARKET_CONTEXT")
for item in [
    ("IMOEX", "equity_index"),
    ("RTSI", "equity_index"),
    ("USD_RUB", "fx_context"),
    ("BRENT", "energy_context"),
    ("GOLD", "metals_context"),
]:
    print(f"CONTEXT code={item[0]} type={item[1]}")

print("")
print("SESSION_CONTEXT")
for session in [
    "ASIA",
    "EUROPE",
    "US",
    "MOSCOW_DAY",
    "MOSCOW_EVENING",
]:
    print(f"SESSION code={session}")

print("")
print("CALENDAR_CONTEXT")
for event in [
    "FOMC",
    "CPI",
    "NFP",
    "OPEC",
    "EXPIRATION",
    "ROLL_PHASE",
]:
    print(f"CALENDAR_EVENT code={event}")

print("")
print("DESIGN_RULES")
for rule in [
    "research_universe_is_baseline_after_architecture_freeze",
    "new_instruments_require_architectural_decision",
    "priority_1_futures_first",
    "priority_2_liquid_equities_only",
    "no_second_or_third_tier_equities_without_decision",
    "contexts_are_optional_dimensions",
    "universe_expansion_must_improve_edge_discovery",
    "no_runtime_execution_changes",
]:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=UNIVERSE_DATA_COVERAGE_AUDIT_V1")
print("next=UNIVERSE_BACKFILL_V1")
print("next=GLOBAL_EDGE_DISCOVERY_V1")

print("")
print("VERDICT=RESEARCH_UNIVERSE_V1_READY")
