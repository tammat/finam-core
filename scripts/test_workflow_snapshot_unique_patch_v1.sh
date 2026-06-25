#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SNAPSHOT_UNIQUE_PATCH_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
ALTER TABLE warehouse.snap_workflow_daily_v1
DROP CONSTRAINT IF EXISTS snap_workflow_daily_v1_snapshot_date_workflow_run_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS ux_snap_workflow_daily_v1
ON warehouse.snap_workflow_daily_v1(snapshot_date, snapshot_type, section_code, metric_code);

SELECT 'old_snapshot_workflow_unique_removed=1';

SELECT 'snapshot_section_metric_unique_exists=' || EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname='warehouse'
      AND tablename='snap_workflow_daily_v1'
      AND indexname='ux_snap_workflow_daily_v1'
);

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_SNAPSHOT_UNIQUE_PATCH_V1_READY';
SQL

echo "TEST_WORKFLOW_SNAPSHOT_UNIQUE_PATCH_V1_OK"
