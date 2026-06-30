#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_EVENT_BAR_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_event_bar_v1.py \
  | tee /tmp/market_data_schema_event_bar_v1.out

grep -q "MARKET_DATA_SCHEMA_EVENT_BAR_V1" /tmp/market_data_schema_event_bar_v1.out
grep -q "table=warehouse.normalized_bar_event_v1" /tmp/market_data_schema_event_bar_v1.out
grep -q "table_exists=true" /tmp/market_data_schema_event_bar_v1.out
grep -q "event_type=BAR_EVENT" /tmp/market_data_schema_event_bar_v1.out
grep -q "event_framework=EVENT_FRAMEWORK_V1" /tmp/market_data_schema_event_bar_v1.out
grep -q "identity_policy=IDENTITY_POLICY_V1" /tmp/market_data_schema_event_bar_v1.out
grep -q "dual_uniqueness=READY" /tmp/market_data_schema_event_bar_v1.out
grep -q "research_ready_flag=READY" /tmp/market_data_schema_event_bar_v1.out
grep -q "ai_ready_flag=READY" /tmp/market_data_schema_event_bar_v1.out
grep -q "partition_ready=1" /tmp/market_data_schema_event_bar_v1.out
grep -q "no_vendor_lock=1" /tmp/market_data_schema_event_bar_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_event_bar_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_event_bar_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_event_bar_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_event_bar_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_event_bar_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_EVENT_BAR_V1_READY" /tmp/market_data_schema_event_bar_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_event_bar_columns_v1.out
SELECT 'bar_has_event_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_bar_event_v1'
      AND column_name='event_uuid'
);

SELECT 'bar_has_event_sequence=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_bar_event_v1'
      AND column_name='event_sequence'
);

SELECT 'bar_has_event_type_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_bar_event_v1'
      AND column_name='event_type_id'
);

SELECT 'bar_has_quality_status_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_bar_event_v1'
      AND column_name='quality_status_id'
);

SELECT 'bar_has_normalization_run_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_bar_event_v1'
      AND column_name='normalization_run_id'
);

SELECT 'bar_has_research_ready=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_bar_event_v1'
      AND column_name='research_ready'
);

SELECT 'bar_has_ai_ready=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_bar_event_v1'
      AND column_name='ai_ready'
);
SQL

grep -q "bar_has_event_uuid=true" /tmp/market_data_schema_event_bar_columns_v1.out
grep -q "bar_has_event_sequence=true" /tmp/market_data_schema_event_bar_columns_v1.out
grep -q "bar_has_event_type_id=true" /tmp/market_data_schema_event_bar_columns_v1.out
grep -q "bar_has_quality_status_id=true" /tmp/market_data_schema_event_bar_columns_v1.out
grep -q "bar_has_normalization_run_id=true" /tmp/market_data_schema_event_bar_columns_v1.out
grep -q "bar_has_research_ready=true" /tmp/market_data_schema_event_bar_columns_v1.out
grep -q "bar_has_ai_ready=true" /tmp/market_data_schema_event_bar_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_EVENT_BAR_V1_OK"
