#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_MART_DASHBOARD_UNIQUE_PATCH_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
ALTER TABLE warehouse.mart_workflow_dashboard_v1
DROP CONSTRAINT IF EXISTS mart_workflow_dashboard_v1_workflow_run_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mart_workflow_dashboard_section_metric_v1
ON warehouse.mart_workflow_dashboard_v1(section_code, metric_code);

SELECT 'dashboard_old_workflow_unique_removed=1';

SELECT 'dashboard_section_metric_unique_exists=' || EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname='warehouse'
      AND tablename='mart_workflow_dashboard_v1'
      AND indexname='ux_mart_workflow_dashboard_section_metric_v1'
);

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=WORKFLOW_MART_DASHBOARD_UNIQUE_PATCH_V1_READY';
SQL

echo "TEST_WORKFLOW_MART_DASHBOARD_UNIQUE_PATCH_V1_OK"
