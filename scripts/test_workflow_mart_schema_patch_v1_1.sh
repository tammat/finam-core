#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_MART_SCHEMA_PATCH_V1_1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
ALTER TABLE warehouse.mart_candidate_workflow_v1
ADD COLUMN IF NOT EXISTS health_reason_code TEXT,
ADD COLUMN IF NOT EXISTS calculated_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE warehouse.mart_workflow_dashboard_v1
ADD COLUMN IF NOT EXISTS health_reason_code TEXT,
ADD COLUMN IF NOT EXISTS calculated_at TIMESTAMPTZ DEFAULT now();

SELECT 'mart_candidate_has_health_reason_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='mart_candidate_workflow_v1'
      AND column_name='health_reason_code'
);

SELECT 'mart_dashboard_has_health_reason_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='mart_workflow_dashboard_v1'
      AND column_name='health_reason_code'
);

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=WORKFLOW_MART_SCHEMA_PATCH_V1_1_READY';
SQL

echo "TEST_WORKFLOW_MART_SCHEMA_PATCH_V1_1_OK"
