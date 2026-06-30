#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_MASTER_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_master_v1.py \
  | tee /tmp/market_data_schema_master_v1.out

grep -q "MARKET_DATA_SCHEMA_MASTER_V1" /tmp/market_data_schema_master_v1.out
grep -q "layer=MASTER_DATA" /tmp/market_data_schema_master_v1.out
grep -q "normalized_source_system_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_asset_class_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_currency_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_venue_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_exchange_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_market_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_asset_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_currency_pair_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_instrument_v1" /tmp/market_data_schema_master_v1.out
grep -q "normalized_contract_v1" /tmp/market_data_schema_master_v1.out
grep -q "tables_found=10" /tmp/market_data_schema_master_v1.out
grep -q "policy=MASTER_REFERENCE_EVENT_QUALITY_LINEAGE" /tmp/market_data_schema_master_v1.out
grep -q "no_vendor_lock=1" /tmp/market_data_schema_master_v1.out
grep -q "source_system=READY" /tmp/market_data_schema_master_v1.out
grep -q "instrument_contract_separated=1" /tmp/market_data_schema_master_v1.out
grep -q "symbol_alias_not_in_master=1" /tmp/market_data_schema_master_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_master_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_master_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_master_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_master_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_master_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_MASTER_V1_READY" /tmp/market_data_schema_master_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_master_columns_v1.out
SELECT 'contract_has_instrument_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_contract_v1'
      AND column_name='instrument_id'
);

SELECT 'contract_has_market_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_contract_v1'
      AND column_name='market_id'
);

SELECT 'instrument_has_asset_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_instrument_v1'
      AND column_name='asset_id'
);

SELECT 'master_has_symbol_alias=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='normalized_symbol_alias_v1'
);
SQL

grep -q "contract_has_instrument_id=true" /tmp/market_data_schema_master_columns_v1.out
grep -q "contract_has_market_id=true" /tmp/market_data_schema_master_columns_v1.out
grep -q "instrument_has_asset_id=true" /tmp/market_data_schema_master_columns_v1.out
grep -q "master_has_symbol_alias=false" /tmp/market_data_schema_master_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_MASTER_V1_OK"
