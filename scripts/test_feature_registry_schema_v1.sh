#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_REGISTRY_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_feature_registry_schema_v1.py \
  | tee /tmp/feature_registry_schema_v1.out

grep -q "FEATURE_REGISTRY_SCHEMA_V1" /tmp/feature_registry_schema_v1.out
grep -q "table=warehouse.feature_registry_v1" /tmp/feature_registry_schema_v1.out
grep -q "status_model=DISCOVERED,REGISTERED,VALIDATED,APPROVED,DEPRECATED,ARCHIVED" /tmp/feature_registry_schema_v1.out
grep -q "maturity_model=RESEARCH,VALIDATED,SHADOW,PAPER,LIVE" /tmp/feature_registry_schema_v1.out
grep -q "source_policy=DISCOVERY_TO_REGISTRY" /tmp/feature_registry_schema_v1.out
grep -q "runtime_changed=0" /tmp/feature_registry_schema_v1.out
grep -q "execution_changed=0" /tmp/feature_registry_schema_v1.out
grep -q "orders_changed=0" /tmp/feature_registry_schema_v1.out
grep -q "fills_changed=0" /tmp/feature_registry_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/feature_registry_schema_v1.out
grep -q "VERDICT=FEATURE_REGISTRY_SCHEMA_V1_READY" /tmp/feature_registry_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'feature_registry_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='feature_registry_v1'
);

SELECT 'feature_registry_columns=' || count(*)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='feature_registry_v1';
SQL

echo "TEST_FEATURE_REGISTRY_SCHEMA_V1_OK"
