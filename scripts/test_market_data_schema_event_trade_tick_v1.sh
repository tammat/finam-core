#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_EVENT_TRADE_TICK_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_event_trade_tick_v1.py \
  | tee /tmp/market_data_schema_event_trade_tick_v1.out

grep -q "MARKET_DATA_SCHEMA_EVENT_TRADE_TICK_V1" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "table=warehouse.normalized_trade_tick_event_v1" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "table_exists=true" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "event_type=TRADE_TICK_EVENT" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "event_classification=MARKET_EVENT" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "event_framework=EVENT_FRAMEWORK_V1" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "identity_policy=IDENTITY_POLICY_V1" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "source_uniqueness=READY" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "exchange_trade_uniqueness=READY" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "microstructure_fields=READY" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "event_hash=READY" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "research_ready_flag=READY" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "ai_ready_flag=READY" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "partition_ready=1" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_event_trade_tick_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_EVENT_TRADE_TICK_V1_READY" /tmp/market_data_schema_event_trade_tick_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_event_trade_tick_columns_v1.out
SELECT 'tick_has_event_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='event_uuid'
);
SELECT 'tick_has_event_sequence=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='event_sequence'
);
SELECT 'tick_has_event_classification=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='event_classification'
);
SELECT 'tick_has_price_currency_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='price_currency_id'
);
SELECT 'tick_has_volume_unit=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='volume_unit'
);
SELECT 'tick_has_tick_direction=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='tick_direction'
);
SELECT 'tick_has_aggressor_side=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='aggressor_side'
);
SELECT 'tick_has_liquidity_flag=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='liquidity_flag'
);
SELECT 'tick_has_exchange_trade_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='exchange_trade_id'
);
SELECT 'tick_has_match_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='match_id'
);
SELECT 'tick_has_trading_day=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='trading_day'
);
SELECT 'tick_has_revision_number=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='revision_number'
);
SELECT 'tick_has_event_hash=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='event_hash'
);
SELECT 'tick_has_research_ready=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='research_ready'
);
SELECT 'tick_has_ai_ready=' || EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='warehouse'
    AND table_name='normalized_trade_tick_event_v1' AND column_name='ai_ready'
);
SQL

grep -q "tick_has_event_uuid=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_event_sequence=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_event_classification=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_price_currency_id=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_volume_unit=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_tick_direction=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_aggressor_side=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_liquidity_flag=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_exchange_trade_id=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_match_id=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_trading_day=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_revision_number=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_event_hash=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_research_ready=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out
grep -q "tick_has_ai_ready=true" /tmp/market_data_schema_event_trade_tick_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_EVENT_TRADE_TICK_V1_OK"
