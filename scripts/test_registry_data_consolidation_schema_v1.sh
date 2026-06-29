#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_DATA_CONSOLIDATION_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_registry_data_consolidation_schema_v1.py \
  | tee /tmp/registry_data_consolidation_schema_v1.out

grep -q "REGISTRY_DATA_CONSOLIDATION_SCHEMA_V1" /tmp/registry_data_consolidation_schema_v1.out
grep -q "таблица=warehouse.registry_relationship_v1" /tmp/registry_data_consolidation_schema_v1.out
grep -q "назначение=единый_слой_связей_registry" /tmp/registry_data_consolidation_schema_v1.out
grep -q "политика=СВЯЗИ_БЕЗ_КОПИРОВАНИЯ_ДАННЫХ" /tmp/registry_data_consolidation_schema_v1.out
grep -q "runtime_changed=0" /tmp/registry_data_consolidation_schema_v1.out
grep -q "execution_changed=0" /tmp/registry_data_consolidation_schema_v1.out
grep -q "orders_changed=0" /tmp/registry_data_consolidation_schema_v1.out
grep -q "fills_changed=0" /tmp/registry_data_consolidation_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/registry_data_consolidation_schema_v1.out
grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_SCHEMA_V1_READY" /tmp/registry_data_consolidation_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'registry_relationship_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='registry_relationship_v1'
);

SELECT 'registry_relationship_columns=' || count(*)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='registry_relationship_v1';
SQL

echo "TEST_REGISTRY_DATA_CONSOLIDATION_SCHEMA_V1_OK"
