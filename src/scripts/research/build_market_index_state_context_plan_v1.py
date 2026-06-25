#!/usr/bin/env python3

print("=== MARKET_INDEX_STATE_CONTEXT_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("")
print("PURPOSE")
print("purpose=add_index_state_context_to_market_state_edge_analysis")
print("purpose=separate_instrument_edge_from_market_regime_edge")
print("purpose=improve_filtering_for_micro_live_candidates")

print("")
print("CONTEXT_MODEL")
contexts = [
    "instrument_state",
    "market_index_state",
    "sector_index_state",
    "fx_state",
    "commodity_index_state",
]
for item in contexts:
    print(f"CONTEXT name={item}")

print("")
print("TARGET_INDEXES")
indexes = [
    ("MOEX_INDEX", "IMOEX_or_MOEX"),
    ("RTS_INDEX", "RTSI_or_RTS"),
    ("MOEX_BLUE_CHIPS", "blue_chip_context_optional"),
    ("USD_RUB", "fx_context_for_ruble_assets"),
    ("BRENT", "commodity_context_for_energy"),
]
for code, role in indexes:
    print(f"INDEX code={code} role={role}")

print("")
print("STATE_DIMENSIONS")
dimensions = [
    "index_trend",
    "index_volatility",
    "index_session",
    "index_risk_regime",
    "index_correlation_to_instrument",
    "index_confirmation",
]
for item in dimensions:
    print(f"DIMENSION name={item}")

print("")
print("LINKING_RULES")
rules = [
    "link_trade_entry_to_nearest_prior_index_state",
    "symbol_state_and_index_state_must_have_independent_signatures",
    "do_not_mix_index_state_into_instrument_signature_v1",
    "store_index_context_as_additional_dimension",
    "edge_scorecard_can_group_by_instrument_state_only",
    "edge_scorecard_can_group_by_instrument_state_plus_index_state",
]
for rule in rules:
    print(f"LINK_RULE name={rule}")

print("")
print("DESIGN_RULES")
design_rules = [
    "index_context_is_research_only",
    "index_context_does_not_change_runtime",
    "index_context_does_not_change_execution",
    "index_context_does_not_send_orders",
    "index_context_must_be_optional",
    "market_state_edge_without_index_context_remains_valid_baseline",
]
for rule in design_rules:
    print(f"rule={rule}")

print("")
print("NEXT_STEPS")
print("next=MARKET_INDEX_SOURCE_DISCOVERY_V1")
print("next=MARKET_INDEX_STATE_SCHEMA_PLAN_V1")
print("next=MARKET_INDEX_STATE_CONTEXT_SCORECARD_V1")

print("")
print("VERDICT=MARKET_INDEX_STATE_CONTEXT_PLAN_READY")
