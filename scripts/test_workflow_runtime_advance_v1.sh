#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_RUNTIME_ADVANCE_V1 ==="

src/scripts/research/build_workflow_runtime_advance_v1.py --save \
  | tee /tmp/workflow_runtime_advance_v1.out

grep -q "WORKFLOW_RUNTIME_ADVANCE_V1" /tmp/workflow_runtime_advance_v1.out
grep -q "mode=save" /tmp/workflow_runtime_advance_v1.out
grep -q "workflow=MSC-000001" /tmp/workflow_runtime_advance_v1.out
grep -q "status=RUNNING" /tmp/workflow_runtime_advance_v1.out
grep -q "current=RISK" /tmp/workflow_runtime_advance_v1.out
grep -q "next=SIGNAL" /tmp/workflow_runtime_advance_v1.out
grep -q "runtime_changed=0" /tmp/workflow_runtime_advance_v1.out
grep -q "execution_changed=0" /tmp/workflow_runtime_advance_v1.out
grep -q "orders_changed=0" /tmp/workflow_runtime_advance_v1.out
grep -q "fills_changed=0" /tmp/workflow_runtime_advance_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_runtime_advance_v1.out
grep -q "VERDICT=WORKFLOW_RUNTIME_ADVANCE_V1_READY" /tmp/workflow_runtime_advance_v1.out

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

SELECT 'advance_events=' || count(*)
FROM research.workflow_runtime_events_v1
WHERE event_type='STAGE_ADVANCED'
  AND stage_from='QUEUE'
  AND stage_to='RISK';
SQL

echo "TEST_WORKFLOW_RUNTIME_ADVANCE_V1_OK"
