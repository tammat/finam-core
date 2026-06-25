#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SNAPSHOT_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_snapshot_builder_v1.py --save \
  | tee /tmp/workflow_snapshot_builder_v1.out

grep -q "WORKFLOW_SNAPSHOT_BUILDER_V1" /tmp/workflow_snapshot_builder_v1.out
grep -q "mode=save" /tmp/workflow_snapshot_builder_v1.out
grep -q "snapshot_today_total=9" /tmp/workflow_snapshot_builder_v1.out
grep -q "snapshot_row=portfolio" /tmp/workflow_snapshot_builder_v1.out
grep -q "snapshot_row=risk" /tmp/workflow_snapshot_builder_v1.out
grep -q "snapshot_row=workflow" /tmp/workflow_snapshot_builder_v1.out
grep -q "snapshot_row=warehouse" /tmp/workflow_snapshot_builder_v1.out
grep -q "snapshot_policy=DAILY_RECALCULABLE_IDEMPOTENT" /tmp/workflow_snapshot_builder_v1.out
grep -q "source_policy=MART_ONLY" /tmp/workflow_snapshot_builder_v1.out
grep -q "presentation_policy=READS_MART_OR_SNAPSHOT_ONLY" /tmp/workflow_snapshot_builder_v1.out
grep -q "read_only_ui_snapshot_ready=1" /tmp/workflow_snapshot_builder_v1.out
grep -q "runtime_changed=0" /tmp/workflow_snapshot_builder_v1.out
grep -q "execution_changed=0" /tmp/workflow_snapshot_builder_v1.out
grep -q "orders_changed=0" /tmp/workflow_snapshot_builder_v1.out
grep -q "fills_changed=0" /tmp/workflow_snapshot_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_snapshot_builder_v1.out
grep -q "VERDICT=WORKFLOW_SNAPSHOT_BUILDER_V1_READY" /tmp/workflow_snapshot_builder_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'snapshot_today_rows=' || count(*)
FROM warehouse.snap_workflow_daily_v1
WHERE snapshot_date=current_date
  AND snapshot_type='READ_ONLY_SYSTEM_STATUS';

SELECT 'snapshot_sections=' ||
       string_agg(section_code || ':' || health_light, ',' ORDER BY section_code)
FROM warehouse.snap_workflow_daily_v1
WHERE snapshot_date=current_date
  AND snapshot_type='READ_ONLY_SYSTEM_STATUS';

SELECT 'snapshot_candidate=' ||
       coalesce(max(candidate_id),'NULL') || '|' ||
       coalesce(max(workflow_run_id)::text,'NULL')
FROM warehouse.snap_workflow_daily_v1
WHERE snapshot_date=current_date
  AND snapshot_type='READ_ONLY_SYSTEM_STATUS';
SQL

echo "TEST_WORKFLOW_SNAPSHOT_BUILDER_V1_OK"
