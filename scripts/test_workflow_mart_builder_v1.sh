#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_MART_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_mart_builder_v1.py --save \
  | tee /tmp/workflow_mart_builder_v1.out

grep -q "WORKFLOW_MART_BUILDER_V1" /tmp/workflow_mart_builder_v1.out
grep -q "mode=save" /tmp/workflow_mart_builder_v1.out
grep -q "mart_candidate_total=1" /tmp/workflow_mart_builder_v1.out
grep -q "mart_dashboard_total=9" /tmp/workflow_mart_builder_v1.out
grep -q "mart_candidate=MSC-000001" /tmp/workflow_mart_builder_v1.out
grep -q "dashboard_row=portfolio" /tmp/workflow_mart_builder_v1.out
grep -q "dashboard_row=risk" /tmp/workflow_mart_builder_v1.out
grep -q "dashboard_row=workflow" /tmp/workflow_mart_builder_v1.out
grep -q "dashboard_row=warehouse" /tmp/workflow_mart_builder_v1.out
grep -q "mart_policy=UI_READY_RECALCULABLE_DATASET" /tmp/workflow_mart_builder_v1.out
grep -q "source_policy=SEMANTIC_ONLY" /tmp/workflow_mart_builder_v1.out
grep -q "presentation_policy=READS_MART_OR_SNAPSHOT_ONLY" /tmp/workflow_mart_builder_v1.out
grep -q "responsive_web_ui_ready=1" /tmp/workflow_mart_builder_v1.out
grep -q "portfolio_first=1" /tmp/workflow_mart_builder_v1.out
grep -q "navigation_standard=HOME_AND_BACK" /tmp/workflow_mart_builder_v1.out
grep -q "runtime_changed=0" /tmp/workflow_mart_builder_v1.out
grep -q "execution_changed=0" /tmp/workflow_mart_builder_v1.out
grep -q "orders_changed=0" /tmp/workflow_mart_builder_v1.out
grep -q "fills_changed=0" /tmp/workflow_mart_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_mart_builder_v1.out
grep -q "VERDICT=WORKFLOW_MART_BUILDER_V1_READY" /tmp/workflow_mart_builder_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'mart_candidate_rows=' || count(*)
FROM warehouse.mart_candidate_workflow_v1;

SELECT 'mart_dashboard_rows=' || count(*)
FROM warehouse.mart_workflow_dashboard_v1;

SELECT 'mart_sections=' ||
       string_agg(section_code || ':' || health_light, ',' ORDER BY (payload->>'display_order')::int)
FROM warehouse.mart_workflow_dashboard_v1;

SELECT 'mart_candidate_latest=' ||
       candidate_id || '|' ||
       workflow_status_code || '|' ||
       current_stage_code || '|' ||
       current_stage_label_ru || '|' ||
       health_light || '|' ||
       health_icon
FROM warehouse.mart_candidate_workflow_v1
ORDER BY updated_at DESC
LIMIT 1;
SQL

echo "TEST_WORKFLOW_MART_BUILDER_V1_OK"
