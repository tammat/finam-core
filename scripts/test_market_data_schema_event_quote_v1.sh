#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_EVENT_QUOTE_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_event_quote_v1.py \
  | tee /tmp/market_data_schema_event_quote_v1.out

grep -q "MARKET_DATA_SCHEMA_EVENT_QUOTE_V1" /tmp/market_data_schema_event_quote_v1.out
grep -q "table=warehouse.normalized_quote_event_v1" /tmp/market_data_schema_event_quote_v1.out
grep -q "table_exists=true" /tmp/market_data_schema_event_quote_v1.out
grep -q "event_type=QUOTE_EVENT" /tmp/market_data_schema_event_quote_v1.out
grep -q "event_framework=EVENT_FRAMEWORK_V1" /tmp/market_data_schema_event_quote_v1.out
grep -q "identity_policy=IDENTITY_POLICY_V1" /tmp/market_data_schema_event_quote_v1.out
grep -q "event_immutability_policy=EVENT_IMMUTABILITY_POLICY_V1" /tmp/market_data_schema_event_quote_v1.out
grep -q "time_policy=EVENT_TIME_POLICY_V1" /tmp/market_data_schema_event_quote_v1.out
grep -q "source_uniqueness=READY" /tmp/market_data_schema_event_quote_v1.out
grep -q "bid_ask_check=READY" /tmp/market_data_schema_event_quote_v1.out
grep -q "spread_generated=READY" /tmp/market_data_schema_event_quote_v1.out
grep -q "research_ready_flag=READY" /tmp/market_data_schema_event_quote_v1.out
grep -q "ai_ready_flag=READY" /tmp/market_data_schema_event_quote_v1.out
grep -q "partition_ready=1" /tmp/market_data_schema_event_quote_v1.out
grep -q "no_vendor_lock=1" /tmp/market_data_schema_event_quote_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_event_quote_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_event_quote_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_event_quote_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_event_quote_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_event_quote_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_EVENT_QUOTE_V1_READY" /tmp/market_data_schema_event_quote_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_event_quote_columns_v1.out
SELECT 'quote_has_event_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='event_uuid'
);

SELECT 'quote_has_event_sequence=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='event_sequence'
);

SELECT 'quote_has_event_type_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='event_type_id'
);

SELECT 'quote_has_quality_status_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='quality_status_id'
);

SELECT 'quote_has_bid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='bid'
);

SELECT 'quote_has_ask=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='ask'
);

SELECT 'quote_has_spread=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='spread'
);

SELECT 'quote_has_research_ready=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='research_ready'
);

SELECT 'quote_has_ai_ready=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_quote_event_v1'
      AND column_name='ai_ready'
);
SQL

grep -q "quote_has_event_uuid=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_event_sequence=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_event_type_id=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_quality_status_id=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_bid=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_ask=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_spread=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_research_ready=true" /tmp/market_data_schema_event_quote_columns_v1.out
grep -q "quote_has_ai_ready=true" /tmp/market_data_schema_event_quote_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_EVENT_QUOTE_V1_OK"
