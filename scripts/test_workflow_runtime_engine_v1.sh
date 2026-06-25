#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_RUNTIME_ENGINE_V1 ==="

src/scripts/research/build_workflow_runtime_engine_v1.py --save \
  | tee /tmp/workflow_runtime_engine_v1.out

grep -q "WORKFLOW_RUNTIME_ENGINE_V1" /tmp/workflow_runtime_engine_v1.out
grep -q "mode=save" /tmp/workflow_runtime_engine_v1.out
grep -q "registry_rows=8" /tmp/workflow_runtime_engine_v1.out
grep -q "workflow_rows=1" /tmp/workflow_runtime_engine_v1.out
grep -q "planned_rows=1" /tmp/workflow_runtime_engine_v1.out
grep -q "workflow_created_events=1" /tmp/workflow_runtime_engine_v1.out
grep -q "workflow=MSC-000001" /tmp/workflow_runtime_engine_v1.out
grep -q "current=QUEUE" /tmp/workflow_runtime_engine_v1.out
grep -q "next=RISK" /tmp/workflow_runtime_engine_v1.out
grep -q "runtime_changed=0" /tmp/workflow_runtime_engine_v1.out
grep -q "execution_changed=0" /tmp/workflow_runtime_engine_v1.out
grep -q "orders_changed=0" /tmp/workflow_runtime_engine_v1.out
grep -q "fills_changed=0" /tmp/workflow_runtime_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_runtime_engine_v1.out
grep -q "VERDICT=WORKFLOW_RUNTIME_ENGINE_V1_READY" /tmp/workflow_runtime_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'registry_pipeline=' || string_agg(stage_name || '->' || coalesce(next_stage,'NULL'), ',' ORDER BY stage_order)
FROM research.workflow_stage_registry_v1
WHERE workflow_type='PAPER_RUNTIME'
  AND workflow_version='v1'
  AND is_active=true;

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

SELECT 'events_total=' || count(*)
FROM research.workflow_runtime_events_v1;
SQL

echo "TEST_WORKFLOW_RUNTIME_ENGINE_V1_OK"
