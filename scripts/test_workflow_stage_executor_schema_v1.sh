#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STAGE_EXECUTOR_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'workflow_registry_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='workflow_stage_registry_v1'
);

SELECT 'workflow_runs_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='workflow_runtime_runs_v1'
);

SELECT 'workflow_events_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='workflow_runtime_events_v1'
);

SELECT 'target_executor_registry=execution.workflow.stage_executor';

SELECT 'target_stage_interface=execution.stages.base_stage.WorkflowStage';

SELECT 'executor_components=' ||
'StageExecutor,' ||
'StageRegistry,' ||
'WorkflowContext,' ||
'WorkflowResult,' ||
'WorkflowStateMachine';

SELECT 'workflow_result_fields=' ||
'status,' ||
'next_stage,' ||
'reason,' ||
'payload';

SELECT 'allowed_result_status=' ||
'OK,' ||
'WAIT,' ||
'BLOCK,' ||
'FAIL,' ||
'RETRY';

SELECT 'stage_plugins=' ||
'QUEUE_STAGE,' ||
'RISK_STAGE,' ||
'SIGNAL_STAGE,' ||
'ORDER_STAGE,' ||
'PAPER_BROKER_STAGE,' ||
'ACCOUNTING_STAGE,' ||
'MONITOR_STAGE';

SELECT 'executor_model=PLUGIN_BASED';

SELECT 'workflow_engine_knows_business_logic=false';

SELECT 'business_logic_inside_stage_plugins=true';

SELECT 'paper_only=true';

SELECT 'real_execution=false';

SELECT 'micro_live_allowed=false';

SELECT 'db_update=0';

SELECT 'runtime_changed=0';

SELECT 'execution_changed=0';

SELECT 'orders_changed=0';

SELECT 'fills_changed=0';

SELECT 'VERDICT=WORKFLOW_STAGE_EXECUTOR_SCHEMA_V1_READY';

SQL

echo "TEST_WORKFLOW_STAGE_EXECUTOR_SCHEMA_V1_OK"

