#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPERIMENT_REGISTRY_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_experiment_registry_schema_v1.py \
  | tee /tmp/experiment_registry_schema_v1.out

grep -q "EXPERIMENT_REGISTRY_SCHEMA_V1" /tmp/experiment_registry_schema_v1.out
grep -q "таблица=warehouse.experiment_registry_v1" /tmp/experiment_registry_schema_v1.out
grep -q "назначение=единый_реестр_исследовательских_экспериментов" /tmp/experiment_registry_schema_v1.out
grep -q "связи=features,models,datasets,reports" /tmp/experiment_registry_schema_v1.out
grep -q "политика_источника=RESEARCH_TO_REGISTRY" /tmp/experiment_registry_schema_v1.out
grep -q "runtime_changed=0" /tmp/experiment_registry_schema_v1.out
grep -q "execution_changed=0" /tmp/experiment_registry_schema_v1.out
grep -q "orders_changed=0" /tmp/experiment_registry_schema_v1.out
grep -q "fills_changed=0" /tmp/experiment_registry_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/experiment_registry_schema_v1.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_SCHEMA_V1_READY" /tmp/experiment_registry_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'experiment_registry_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='experiment_registry_v1'
);

SELECT 'experiment_registry_columns=' || count(*)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='experiment_registry_v1';
SQL

echo "TEST_EXPERIMENT_REGISTRY_SCHEMA_V1_OK"
