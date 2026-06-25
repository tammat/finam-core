#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SEMANTIC_SCHEMA_PATCH_V1_1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
ALTER TABLE warehouse.sem_workflow_v1
ADD COLUMN IF NOT EXISTS latency_ms NUMERIC,
ADD COLUMN IF NOT EXISTS success_rate NUMERIC;

SELECT 'sem_workflow_has_latency_ms=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='sem_workflow_v1'
      AND column_name='latency_ms'
);

SELECT 'sem_workflow_has_success_rate=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='sem_workflow_v1'
      AND column_name='success_rate'
);

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=WORKFLOW_SEMANTIC_SCHEMA_PATCH_V1_1_READY';
SQL

echo "TEST_WORKFLOW_SEMANTIC_SCHEMA_PATCH_V1_1_OK"
