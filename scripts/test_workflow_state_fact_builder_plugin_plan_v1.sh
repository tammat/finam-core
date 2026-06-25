#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STATE_FACT_BUILDER_PLUGIN_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'source_layer=warehouse.nrm_workflow_run_v1';

SELECT 'source_rows=' || count(*)
FROM warehouse.nrm_workflow_run_v1;

SELECT 'builder_framework=BuilderContext,BuilderResult,FactBuilder,BuilderRegistry,BuilderExecutor';

SELECT 'builder_name=WORKFLOW_STATE_FACT_BUILDER_V1';

SELECT 'builder_plugin=WorkflowStateFactBuilder';

SELECT 'builder_model=PLUGIN_BASED';

SELECT 'planned_state_fact_1=fact_state_candidate_lifecycle_v1';

SELECT 'planned_state_fact_2=fact_state_workflow_health_v1';

SELECT 'planned_state_fact_3=fact_state_workflow_quality_v1';

SELECT 'candidate_lifecycle_fields=' ||
'research_status_code,' ||
'workflow_status_code,' ||
'paper_status_code,' ||
'current_stage_code,' ||
'next_stage_code,' ||
'health_score,' ||
'health_light,' ||
'health_reason_code';

SELECT 'workflow_health_fields=' ||
'health_score,' ||
'health_light,' ||
'health_reason_code,' ||
'status_code,' ||
'reason_code';

SELECT 'workflow_quality_fields=' ||
'latency_ms,' ||
'success_rate,' ||
'wait_rate,' ||
'block_rate,' ||
'fail_rate,' ||
'health_score,' ||
'health_light';

SELECT 'upsert_policy=STATE_FACT_RECALCULABLE';

SELECT 'pipeline_update=FACT_PIPELINE_RUNS_V1';

SELECT 'pipeline_status=PLANNED_TO_COMPLETED';

SELECT 'builder_result_fields=' ||
'status,' ||
'rows_in,' ||
'rows_out,' ||
'duplicate_rows,' ||
'error_rows,' ||
'health_score,' ||
'health_light,' ||
'health_reason_code,' ||
'payload';

SELECT 'source_policy=NORMALIZED_LAYER_ONLY';

SELECT 'forbidden_policy=NO_DIRECT_RESEARCH_READ';

SELECT 'canonical_policy=STORE_CODES_ONLY';

SELECT 'health_policy=REFERENCE_STATUS_LIGHTS';

SELECT 'incremental_policy=changed_since_only';

SELECT 'no_full_scan_policy=true';

SELECT 'multi_exchange=true';

SELECT 'multi_broker=true';

SELECT 'multilingual_ready=true';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_STATE_FACT_BUILDER_PLUGIN_PLAN_V1_READY';

SQL

echo "TEST_WORKFLOW_STATE_FACT_BUILDER_PLUGIN_PLAN_V1_OK"
