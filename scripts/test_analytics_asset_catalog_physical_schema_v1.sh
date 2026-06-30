#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_ANALYTICS_ASSET_CATALOG_PHYSICAL_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_analytics_asset_catalog_physical_schema_v1.py --save \
  | tee /tmp/analytics_asset_catalog_physical_schema_v1.out

grep -q "ANALYTICS_ASSET_CATALOG_PHYSICAL_SCHEMA_V1" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "mode=save" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "table=warehouse.analytics_asset_catalog_v1" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "source_of_truth_ready=1" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "lineage_ready=1" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "impact_analysis_ready=1" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "ai_layer_ready=1" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "feature_model_platform_ready=1" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "runtime_changed=0" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "execution_changed=0" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "orders_changed=0" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "fills_changed=0" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/analytics_asset_catalog_physical_schema_v1.out
grep -q "VERDICT=ANALYTICS_ASSET_CATALOG_PHYSICAL_SCHEMA_V1_READY" /tmp/analytics_asset_catalog_physical_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'catalog_table_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='analytics_asset_catalog_v1'
);

SELECT 'catalog_columns=' || count(*)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='analytics_asset_catalog_v1';

SELECT 'catalog_key_fields=' ||
       string_agg(column_name, ',' ORDER BY column_name)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='analytics_asset_catalog_v1'
  AND column_name IN (
      'object_id','domain','category','source_system','source_of_truth',
      'upstream_objects','downstream_objects','ai_enabled','model_code',
      'knowledge_class','cutover_status'
  );
SQL

echo "TEST_ANALYTICS_ASSET_CATALOG_PHYSICAL_SCHEMA_V1_OK"
