#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_REFERENCE_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_reference_v1.py \
  | tee /tmp/market_data_schema_reference_v1.out

grep -q "MARKET_DATA_SCHEMA_REFERENCE_V1" /tmp/market_data_schema_reference_v1.out
grep -q "layer=REFERENCE_DATA" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_symbol_alias_v1" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_timeframe_v1" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_trading_session_v1" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_trading_calendar_v1" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_holiday_v1" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_roll_schedule_v1" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_corporate_action_v1" /tmp/market_data_schema_reference_v1.out
grep -q "normalized_market_regime_v1" /tmp/market_data_schema_reference_v1.out
grep -q "tables_found=8" /tmp/market_data_schema_reference_v1.out
grep -q "symbol_alias=READY" /tmp/market_data_schema_reference_v1.out
grep -q "timeframe=READY" /tmp/market_data_schema_reference_v1.out
grep -q "trading_session=READY" /tmp/market_data_schema_reference_v1.out
grep -q "trading_calendar=READY" /tmp/market_data_schema_reference_v1.out
grep -q "holiday=READY" /tmp/market_data_schema_reference_v1.out
grep -q "roll_schedule=READY" /tmp/market_data_schema_reference_v1.out
grep -q "corporate_action=READY" /tmp/market_data_schema_reference_v1.out
grep -q "market_regime=READY" /tmp/market_data_schema_reference_v1.out
grep -q "history_support=READY" /tmp/market_data_schema_reference_v1.out
grep -q "master_to_reference_dependency=ONE_WAY" /tmp/market_data_schema_reference_v1.out
grep -q "no_vendor_lock=1" /tmp/market_data_schema_reference_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_reference_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_reference_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_reference_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_reference_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_reference_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_REFERENCE_V1_READY" /tmp/market_data_schema_reference_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_reference_columns_v1.out
SELECT 'symbol_alias_has_source_system_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_symbol_alias_v1'
      AND column_name='source_system_id'
);

SELECT 'symbol_alias_has_instrument_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_symbol_alias_v1'
      AND column_name='instrument_id'
);

SELECT 'symbol_alias_has_contract_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_symbol_alias_v1'
      AND column_name='contract_id'
);

SELECT 'timeframe_has_aggregation_family=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_timeframe_v1'
      AND column_name='aggregation_family'
);

SELECT 'roll_schedule_has_next_contract_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_roll_schedule_v1'
      AND column_name='next_contract_id'
);

SELECT 'corporate_action_has_adjust_price=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_corporate_action_v1'
      AND column_name='adjust_price'
);

SELECT 'corporate_action_has_adjust_volume=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_corporate_action_v1'
      AND column_name='adjust_volume'
);
SQL

grep -q "symbol_alias_has_source_system_id=true" /tmp/market_data_schema_reference_columns_v1.out
grep -q "symbol_alias_has_instrument_id=true" /tmp/market_data_schema_reference_columns_v1.out
grep -q "symbol_alias_has_contract_id=true" /tmp/market_data_schema_reference_columns_v1.out
grep -q "timeframe_has_aggregation_family=true" /tmp/market_data_schema_reference_columns_v1.out
grep -q "roll_schedule_has_next_contract_id=true" /tmp/market_data_schema_reference_columns_v1.out
grep -q "corporate_action_has_adjust_price=true" /tmp/market_data_schema_reference_columns_v1.out
grep -q "corporate_action_has_adjust_volume=true" /tmp/market_data_schema_reference_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_REFERENCE_V1_OK"
