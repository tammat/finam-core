#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_EVENT_CORE_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_event_core_v1.py \
  | tee /tmp/market_data_schema_event_core_v1.out

grep -q "MARKET_DATA_SCHEMA_EVENT_CORE_V1" /tmp/market_data_schema_event_core_v1.out
grep -q "layer=EVENT_CORE" /tmp/market_data_schema_event_core_v1.out
grep -q "normalized_event_type_v1" /tmp/market_data_schema_event_core_v1.out
grep -q "normalized_quality_status_v1" /tmp/market_data_schema_event_core_v1.out
grep -q "normalized_normalization_run_v1" /tmp/market_data_schema_event_core_v1.out
grep -q "normalized_event_sequence_v1" /tmp/market_data_schema_event_core_v1.out
grep -q "tables_found=4" /tmp/market_data_schema_event_core_v1.out
grep -q "event_type=READY" /tmp/market_data_schema_event_core_v1.out
grep -q "quality_status=READY" /tmp/market_data_schema_event_core_v1.out
grep -q "normalization_run=READY" /tmp/market_data_schema_event_core_v1.out
grep -q "event_sequence=READY" /tmp/market_data_schema_event_core_v1.out
grep -q "event_framework=EVENT_FRAMEWORK_V1" /tmp/market_data_schema_event_core_v1.out
grep -q "identity_policy=IDENTITY_POLICY_V1" /tmp/market_data_schema_event_core_v1.out
grep -q "event_core_policy=EVENT_CORE_POLICY_V1" /tmp/market_data_schema_event_core_v1.out
grep -q "no_vendor_lock=1" /tmp/market_data_schema_event_core_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_event_core_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_event_core_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_event_core_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_event_core_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_event_core_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_EVENT_CORE_V1_READY" /tmp/market_data_schema_event_core_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_event_core_columns_v1.out
SELECT 'event_type_has_event_domain=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_event_type_v1'
      AND column_name='event_domain'
);

SELECT 'quality_has_ai_flag=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quality_status_v1'
      AND column_name='is_usable_for_ai'
);

SELECT 'normalization_run_has_run_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_normalization_run_v1'
      AND column_name='run_uuid'
);

SELECT 'normalization_run_has_git_commit=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_normalization_run_v1'
      AND column_name='git_commit'
);

SELECT 'event_sequence_has_current_value=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_event_sequence_v1'
      AND column_name='current_value'
);

SELECT 'event_type_bar_exists=' || EXISTS (
    SELECT 1 FROM warehouse.normalized_event_type_v1
    WHERE entity_code='BAR_EVENT'
);

SELECT 'quality_valid_exists=' || EXISTS (
    SELECT 1 FROM warehouse.normalized_quality_status_v1
    WHERE entity_code='VALID'
);
SQL

grep -q "event_type_has_event_domain=true" /tmp/market_data_schema_event_core_columns_v1.out
grep -q "quality_has_ai_flag=true" /tmp/market_data_schema_event_core_columns_v1.out
grep -q "normalization_run_has_run_uuid=true" /tmp/market_data_schema_event_core_columns_v1.out
grep -q "normalization_run_has_git_commit=true" /tmp/market_data_schema_event_core_columns_v1.out
grep -q "event_sequence_has_current_value=true" /tmp/market_data_schema_event_core_columns_v1.out
grep -q "event_type_bar_exists=true" /tmp/market_data_schema_event_core_columns_v1.out
grep -q "quality_valid_exists=true" /tmp/market_data_schema_event_core_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_EVENT_CORE_V1_OK"
