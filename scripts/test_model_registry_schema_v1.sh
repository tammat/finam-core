#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MODEL_REGISTRY_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_model_registry_schema_v1.py \
  | tee /tmp/model_registry_schema_v1.out

grep -q "MODEL_REGISTRY_SCHEMA_V1" /tmp/model_registry_schema_v1.out
grep -q "table=warehouse.model_registry_v1" /tmp/model_registry_schema_v1.out
grep -q "status_model=DISCOVERED,REGISTERED,VALIDATED,APPROVED,DEPRECATED,ARCHIVED" /tmp/model_registry_schema_v1.out
grep -q "maturity_model=RESEARCH,VALIDATED,SHADOW,PAPER,LIVE" /tmp/model_registry_schema_v1.out
grep -q "source_policy=DISCOVERY_TO_REGISTRY" /tmp/model_registry_schema_v1.out
grep -q "runtime_changed=0" /tmp/model_registry_schema_v1.out
grep -q "execution_changed=0" /tmp/model_registry_schema_v1.out
grep -q "orders_changed=0" /tmp/model_registry_schema_v1.out
grep -q "fills_changed=0" /tmp/model_registry_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/model_registry_schema_v1.out
grep -q "VERDICT=MODEL_REGISTRY_SCHEMA_V1_READY" /tmp/model_registry_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'model_registry_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='model_registry_v1'
);

SELECT 'model_registry_columns=' || count(*)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='model_registry_v1';
SQL

echo "TEST_MODEL_REGISTRY_SCHEMA_V1_OK"
