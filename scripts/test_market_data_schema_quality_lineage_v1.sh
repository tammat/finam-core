#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_SCHEMA_QUALITY_LINEAGE_V1 ==="

PYTHONPATH=src src/scripts/research/build_market_data_schema_quality_lineage_v1.py \
  | tee /tmp/market_data_schema_quality_lineage_v1.out

grep -q "MARKET_DATA_SCHEMA_QUALITY_LINEAGE_V1" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "layer=QUALITY_LINEAGE" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "tables_found=2" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "relationship_types=13" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "lineage_graph=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "root_entity_uuid=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "parent_lineage_uuid=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "source_entity_uuid=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "target_entity_uuid=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "path_hash=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "graph_node_uuid=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "explainability_score=READY" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "runtime_changed=0" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "execution_changed=0" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "orders_changed=0" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "fills_changed=0" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_schema_quality_lineage_v1.out
grep -q "VERDICT=MARKET_DATA_SCHEMA_QUALITY_LINEAGE_V1_READY" /tmp/market_data_schema_quality_lineage_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/market_data_schema_quality_lineage_columns_v1.out
SELECT 'lineage_has_lineage_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_lineage_event_v1'
      AND column_name='lineage_uuid'
);
SELECT 'lineage_has_root_entity_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_lineage_event_v1'
      AND column_name='root_entity_uuid'
);
SELECT 'lineage_has_graph_node_uuid=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='normalized_lineage_event_v1'
      AND column_name='graph_node_uuid'
);
SELECT 'relationship_explained_by_exists=' || EXISTS (
    SELECT 1 FROM warehouse.normalized_lineage_relationship_type_v1
    WHERE entity_code='EXPLAINED_BY'
);
SQL

grep -q "lineage_has_lineage_uuid=true" /tmp/market_data_schema_quality_lineage_columns_v1.out
grep -q "lineage_has_root_entity_uuid=true" /tmp/market_data_schema_quality_lineage_columns_v1.out
grep -q "lineage_has_graph_node_uuid=true" /tmp/market_data_schema_quality_lineage_columns_v1.out
grep -q "relationship_explained_by_exists=true" /tmp/market_data_schema_quality_lineage_columns_v1.out

echo "TEST_MARKET_DATA_SCHEMA_QUALITY_LINEAGE_V1_OK"
