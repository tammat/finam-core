#!/usr/bin/env python3

print("=== RESEARCH_CANONICAL_SCHEMA_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

tables = {
    "research_market_bars_v1": [
        "symbol", "asset_class", "timeframe", "ts",
        "open", "high", "low", "close", "volume",
        "source_table", "source_id", "data_quality",
    ],
    "research_trade_facts_v1": [
        "trade_id", "symbol", "asset_class", "strategy", "trade_source",
        "entry_ts", "exit_ts", "entry_price", "exit_price",
        "gross_pnl", "commission", "net_pnl",
        "holding_minutes", "direction", "quality_flag",
    ],
    "research_trade_feature_snapshots_v1": [
        "trade_id", "snapshot_ts", "snapshot_type",
        "atr_pct", "volume_ratio", "momentum_1", "momentum_3",
        "compression_ratio", "breakout_distance_pct", "session_bucket",
    ],
    "research_market_state_context_v1": [
        "context_ts", "factor_group", "factor_name", "state",
        "impact_scope", "impact_direction", "impact_strength",
        "confidence", "valid_from", "valid_to", "source",
    ],
}

print("\nCANONICAL_TABLES")
for table, cols in tables.items():
    print(f"TABLE name={table} columns={','.join(cols)}")

print("\nDESIGN_RULES")
print("rule=do_not_replace_operational_tables")
print("rule=research_layer_is_read_model")
print("rule=all_features_join_to_trade_id_or_ts_symbol_timeframe")
print("rule=market_state_context_is_extensible_by_rows_not_columns")
print("rule=no_runtime_execution_changes")

print("\nVERDICT=RESEARCH_CANONICAL_SCHEMA_PLAN_READY")
