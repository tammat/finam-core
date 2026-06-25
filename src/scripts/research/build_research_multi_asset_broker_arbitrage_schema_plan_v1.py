#!/usr/bin/env python3

print("=== RESEARCH_MULTI_ASSET_BROKER_ARBITRAGE_SCHEMA_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

tables = {
    "research.brokers_v1": [
        "broker_id", "broker_name", "country", "api_type",
        "commission_model", "currency", "is_active"
    ],
    "research.exchanges_v1": [
        "exchange_id", "exchange_code", "exchange_name",
        "country", "timezone", "currency", "market_type"
    ],
    "research.instruments_v1": [
        "instrument_id", "ticker", "instrument_name",
        "asset_class", "instrument_type", "currency",
        "isin", "base_currency", "quote_currency",
        "underlying_symbol", "maturity_date", "expiration_date"
    ],
    "research.instrument_listings_v1": [
        "listing_id", "instrument_id", "exchange_id", "broker_id",
        "broker_symbol", "exchange_symbol", "lot_size",
        "price_step", "price_step_value", "session_calendar"
    ],
    "research.arbitrage_pairs_v1": [
        "pair_id", "arbitrage_type", "left_instrument_id",
        "right_instrument_id", "third_instrument_id",
        "hedge_ratio", "spread_formula", "currency_adjustment",
        "commission_model", "slippage_model", "is_active"
    ],
}

print("\nTABLES")
for table, cols in tables.items():
    print(f"TABLE name={table} columns={','.join(cols)}")

print("\nDESIGN_RULES")
print("rule=multi_broker_ready")
print("rule=multi_exchange_ready")
print("rule=multi_asset_ready")
print("rule=arbitrage_is_multi_leg_not_single_trade")
print("rule=all_report_times_msk")
print("rule=all_user_messages_ru")
print("rule=no_runtime_execution_changes")

print("\nVERDICT=RESEARCH_MULTI_ASSET_BROKER_ARBITRAGE_SCHEMA_PLAN_READY")
