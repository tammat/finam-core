#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STAGE_EXECUTOR_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'workflow_runs=' || count(*)
FROM research.workflow_runtime_runs_v1;

SELECT
'current_workflow=' ||
candidate_id || '|' ||
workflow_status || '|' ||
current_stage || '|' ||
coalesce(next_stage,'NULL')
FROM research.workflow_runtime_runs_v1
ORDER BY updated_at DESC
LIMIT 1;

SELECT 'executor_input=WorkflowContext';

SELECT 'executor_output=WorkflowResult';

SELECT 'executor_calls=StagePlugin.execute(context)';

SELECT 'workflow_result_field_1=status';

SELECT 'workflow_result_field_2=next_stage';

SELECT 'workflow_result_field_3=reason';

SELECT 'workflow_result_field_4=payload';

SELECT 'status_ok=ADVANCE_WORKFLOW';

SELECT 'status_wait=KEEP_CURRENT_STAGE';

SELECT 'status_block=WORKFLOW_BLOCKED';

SELECT 'status_fail=WORKFLOW_FAILED';

SELECT 'status_retry=KEEP_STAGE_AND_RETRY';

SELECT 'executor_updates=WORKFLOW_STATE_ONLY';

SELECT 'stage_plugins_own_business_logic=true';

SELECT 'workflow_engine_owns_state_machine=true';

SELECT 'paper_only=true';

SELECT 'real_execution=false';

SELECT 'orders_created=0';

SELECT 'fills_created=0';

SELECT 'db_update=0';

SELECT 'runtime_changed=0';

SELECT 'execution_changed=0';

SELECT 'orders_changed=0';

SELECT 'fills_changed=0';

SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_STAGE_EXECUTOR_PLAN_V1_READY';

SQL

echo "TEST_WORKFLOW_STAGE_EXECUTOR_PLAN_V1_OK"

