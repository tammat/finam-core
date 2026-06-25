#!/usr/bin/env python3

print("=== TRADE_FACTS_CANONICAL_SOURCE_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("\nCANONICAL_SOURCE_DECISION")
print("canonical_source=public.trade_outcomes")
print("fallback_source=public.closed_trade_chains_v3")
print("excluded_source=research.trade_facts")
print("reason=research.trade_facts_table_not_exists")
print("reason=trade_outcomes_has_entry_exit_ts_net_pnl_commission_payload")

print("\nCANONICAL_COLUMNS")
columns = [
    "trade_id",
    "symbol",
    "strategy",
    "timeframe",
    "trade_source",
    "entry_ts",
    "exit_ts",
    "side",
    "qty",
    "entry_price",
    "exit_price",
    "gross_pnl",
    "commission",
    "net_pnl",
    "payload_or_raw_json",
]
for col in columns:
    print(f"COLUMN name={col}")

print("\nSOURCE_MAPPING")
mapping = [
    ("trade_id", "id"),
    ("symbol", "symbol"),
    ("strategy", "strategy"),
    ("timeframe", "timeframe"),
    ("trade_source", "trade_source"),
    ("entry_ts", "entry_ts"),
    ("exit_ts", "exit_ts"),
    ("side", "entry_side"),
    ("qty", "qty"),
    ("entry_price", "entry_price"),
    ("exit_price", "exit_price"),
    ("gross_pnl", "gross_pnl"),
    ("commission", "commission"),
    ("net_pnl", "net_pnl"),
    ("payload_or_raw_json", "raw_json"),
]
for target, source in mapping:
    print(f"MAP target={target} source=public.trade_outcomes.{source}")

print("\nFILTERS")
filters = [
    "trade_source_class_from_raw_json_if_exists",
    "prefer_trade_source=RUNTIME_OR_PAPER_CLEAN_ENOUGH",
    "exclude_trade_source=HISTORICAL_REPLAY_FOR_MICRO_LIVE",
    "exclude_trade_source=LEGACY_NG_SYNTHETIC_BACKFILL",
    "entry_ts_is_not_null",
    "symbol_is_not_null",
]
for item in filters:
    print(f"FILTER name={item}")

print("\nDESIGN_RULES")
rules = [
    "canonical_trade_source_is_public_trade_outcomes",
    "closed_trade_chains_v3_is_fallback_only",
    "research_trade_facts_not_required",
    "market_state_trade_linker_must_use_existing_canonical_source",
    "no_runtime_execution_changes",
]
for rule in rules:
    print(f"rule={rule}")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_TRADE_LINKING_IMPLEMENTATION_V1_1")

print("\nVERDICT=TRADE_FACTS_CANONICAL_SOURCE_PLAN_READY")
