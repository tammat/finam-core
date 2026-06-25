#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STAGE_RESULT_APPLY_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_stage_result_apply_v1.py --save \
  | tee /tmp/workflow_stage_result_apply_v1.out

grep -q "WORKFLOW_STAGE_RESULT_APPLY_V1" /tmp/workflow_stage_result_apply_v1.out
grep -q "mode=save" /tmp/workflow_stage_result_apply_v1.out
grep -q "applied_rows=1" /tmp/workflow_stage_result_apply_v1.out
grep -q "workflow=MSC-000001" /tmp/workflow_stage_result_apply_v1.out
grep -q "status=RUNNING" /tmp/workflow_stage_result_apply_v1.out
grep -q "current=SIGNAL" /tmp/workflow_stage_result_apply_v1.out
grep -q "next=ORDER" /tmp/workflow_stage_result_apply_v1.out
grep -q "applied_events=1" /tmp/workflow_stage_result_apply_v1.out
grep -q "runtime_changed=0" /tmp/workflow_stage_result_apply_v1.out
grep -q "execution_changed=0" /tmp/workflow_stage_result_apply_v1.out
grep -q "orders_changed=0" /tmp/workflow_stage_result_apply_v1.out
grep -q "fills_changed=0" /tmp/workflow_stage_result_apply_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_stage_result_apply_v1.out
grep -q "VERDICT=WORKFLOW_STAGE_RESULT_APPLY_V1_READY" /tmp/workflow_stage_result_apply_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'workflow_latest=' ||
       candidate_id || '|' ||
       workflow_status || '|' ||
       current_stage || '|' ||
       coalesce(next_stage,'NULL')
FROM research.workflow_runtime_runs_v1
WHERE workflow_type='PAPER_RUNTIME'
  AND workflow_version='v1'
ORDER BY updated_at DESC
LIMIT 1;

SELECT 'result_applied_events=' || count(*)
FROM research.workflow_runtime_events_v1
WHERE event_type='STAGE_RESULT_APPLIED'
  AND stage_from='RISK'
  AND stage_to='SIGNAL'
  AND event_status='OK';
SQL

echo "TEST_WORKFLOW_STAGE_RESULT_APPLY_V1_OK"
