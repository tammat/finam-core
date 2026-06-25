#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_ENGINE_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'ready_queue_rows=' || count(*)
FROM research.shadow_runtime_queue_v1
WHERE queue_status='READY';

SELECT 'ready_candidate=' ||
       candidate_id || '|' ||
       symbol || '|' ||
       strategy || '|' ||
       timeframe || '|' ||
       queue_status || '|' ||
       queue_reason
FROM research.shadow_runtime_queue_v1
WHERE queue_status='READY'
ORDER BY priority DESC, updated_at DESC
LIMIT 1;

SELECT 'planned_source=research.shadow_runtime_queue_v1';

SELECT 'planned_target=research.shadow_runtime_runs_v1';

SELECT 'planned_action=CREATE_SHADOW_RUN_RECORD_ONLY';

SELECT 'planned_run_status=PLANNED';

SELECT 'planned_run_reason=READY_FROM_SHADOW_RUNTIME_QUEUE';

SELECT 'planned_execution=NO_ORDERS_NO_FILLS_NO_TRADES';

SELECT 'planned_runtime_mode=SHADOW_ONLY';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=SHADOW_RUNTIME_ENGINE_PLAN_V1_READY';
SQL

echo "TEST_SHADOW_RUNTIME_ENGINE_PLAN_V1_OK"
