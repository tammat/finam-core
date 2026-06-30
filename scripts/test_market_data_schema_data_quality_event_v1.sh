#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_DATA_QUALITY_EVENT_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_data_quality_event_v1.py \
  | tee /tmp/market_data_schema_data_quality_event_v1.out

grep -q "MARKET_DATA_SCHEMA_DATA_QUALITY_EVENT_V1" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "layer=QUALITY_EVENT" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "normalized_quality_reason_v1" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "normalized_resolution_method_v1" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "normalized_data_quality_event_v1" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "tables_found=3" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "quality_reason=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "resolution_method=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "data_quality_event=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "quality_governance=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "quality_dimensions=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "affected_event_uuid=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "affected_entity_uuid=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "blocks_research=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "blocks_ai=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "blocks_runtime=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "confidence=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "resolution_tracking=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "ai_explained=READY" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "event_framework=EVENT_FRAMEWORK_V1" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "identity_policy=IDENTITY_POLICY_V1" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_data_quality_event_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_DATA_QUALITY_EVENT_V1_READY" /tmp/market_data_schema_data_quality_event_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_data_quality_event_columns_v1.out
SELECT 'quality_has_affected_event_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='affected_event_uuid'
);
SELECT 'quality_has_affected_entity_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='affected_entity_uuid'
);
SELECT 'quality_has_quality_reason_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='quality_reason_id'
);
SELECT 'quality_has_resolution_method_id=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='resolution_method_id'
);
SELECT 'quality_has_blocks_research=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='blocks_research'
);
SELECT 'quality_has_blocks_ai=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='blocks_ai'
);
SELECT 'quality_has_blocks_runtime=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='blocks_runtime'
);
SELECT 'quality_has_confidence=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='confidence'
);
SELECT 'quality_has_resolved=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='resolved'
);
SELECT 'quality_has_ai_explained=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_data_quality_event_v1'
      AND column_name='ai_explained'
);
SELECT 'reason_bad_tick_exists=' || EXISTS (
    SELECT 1 FROM warehouse.normalized_quality_reason_v1
    WHERE entity_code='BAD_TICK'
);
SELECT 'resolution_rebuild_exists=' || EXISTS (
    SELECT 1 FROM warehouse.normalized_resolution_method_v1
    WHERE entity_code='REBUILD'
);
SQL

grep -q "quality_has_affected_event_uuid=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_affected_entity_uuid=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_quality_reason_id=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_resolution_method_id=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_blocks_research=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_blocks_ai=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_blocks_runtime=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_confidence=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_resolved=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "quality_has_ai_explained=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "reason_bad_tick_exists=true" /tmp/market_data_schema_data_quality_event_columns_v1.out
grep -q "resolution_rebuild_exists=true" /tmp/market_data_schema_data_quality_event_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_DATA_QUALITY_EVENT_V1_OK"
