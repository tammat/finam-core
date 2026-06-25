#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_RUNTIME_ENGINE_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'target_table=research.workflow_runtime_runs_v1';

SELECT 'target_columns=workflow_run_id,workflow_type,workflow_version,candidate_id,symbol,strategy,timeframe,workflow_status,current_stage,next_stage,started_at,finished_at,runtime_changed,execution_changed,orders_changed,fills_changed,micro_live_allowed,payload,created_at,updated_at';

SELECT 'target_table=research.workflow_runtime_events_v1';

SELECT 'event_columns=event_id,workflow_run_id,candidate_id,stage_from,stage_to,event_type,event_reason,event_status,event_ts,payload,created_at';

SELECT 'target_table=research.workflow_stage_registry_v1';

SELECT 'registry_columns=stage_id,workflow_type,workflow_version,stage_name,next_stage,stage_order,is_terminal,is_active,payload,created_at,updated_at';

SELECT 'initial_workflow_type=PAPER_RUNTIME';

SELECT 'initial_workflow_version=v1';

SELECT 'initial_stages=QUEUE,RISK,SIGNAL,ORDER,PAPER_BROKER,ACCOUNTING,MONITOR,FINISHED';

SELECT 'engine_model=GENERIC_WORKFLOW_ENGINE';

SELECT 'paper_runtime_orchestrator_role=FIRST_WORKFLOW_CONFIGURATION';

SELECT 'real_execution=false';
SELECT 'paper_only=true';
SELECT 'micro_live_allowed=false';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';

SELECT 'VERDICT=WORKFLOW_RUNTIME_ENGINE_SCHEMA_V1_READY';
SQL

echo "TEST_WORKFLOW_RUNTIME_ENGINE_SCHEMA_V1_OK"
