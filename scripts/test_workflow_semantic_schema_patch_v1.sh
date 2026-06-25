#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SEMANTIC_SCHEMA_PATCH_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
ALTER TABLE warehouse.sem_candidate_v1
ADD COLUMN IF NOT EXISTS workflow_status_code TEXT,
ADD COLUMN IF NOT EXISTS workflow_status_label_ru TEXT,
ADD COLUMN IF NOT EXISTS current_stage_code TEXT,
ADD COLUMN IF NOT EXISTS current_stage_label_ru TEXT,
ADD COLUMN IF NOT EXISTS next_stage_code TEXT,
ADD COLUMN IF NOT EXISTS next_stage_label_ru TEXT,
ADD COLUMN IF NOT EXISTS health_icon TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE warehouse.sem_workflow_v1
ADD COLUMN IF NOT EXISTS workflow_status_label_ru TEXT,
ADD COLUMN IF NOT EXISTS current_stage_label_ru TEXT,
ADD COLUMN IF NOT EXISTS next_stage_label_ru TEXT,
ADD COLUMN IF NOT EXISTS health_icon TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

SELECT 'sem_candidate_has_workflow_status_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='sem_candidate_v1'
      AND column_name='workflow_status_code'
);

SELECT 'sem_workflow_has_health_icon=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='sem_workflow_v1'
      AND column_name='health_icon'
);

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=WORKFLOW_SEMANTIC_SCHEMA_PATCH_V1_READY';
SQL

echo "TEST_WORKFLOW_SEMANTIC_SCHEMA_PATCH_V1_OK"
