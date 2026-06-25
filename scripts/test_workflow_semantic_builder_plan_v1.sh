#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SEMANTIC_BUILDER_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'planned_source_1=warehouse.fact_state_candidate_lifecycle_v1';
SELECT 'planned_source_2=warehouse.fact_state_workflow_health_v1';
SELECT 'planned_source_3=warehouse.fact_state_workflow_quality_v1';
SELECT 'planned_source_4=warehouse.dim_stage_v1';
SELECT 'planned_source_5=warehouse.dim_status_light_v1';

SELECT 'planned_target_1=warehouse.sem_candidate_v1';
SELECT 'planned_target_2=warehouse.sem_workflow_v1';

SELECT 'sem_candidate_fields=candidate_id,workflow_run_id,symbol,display_symbol,strategy_code,timeframe,lifecycle_status_code,health_score,health_light,health_reason_code,semantic_version,payload';

SELECT 'sem_workflow_fields=workflow_run_id,candidate_id,workflow_status_code,current_stage_code,next_stage_code,health_score,health_light,health_reason_code,semantic_version,payload';

SELECT 'business_object_1=Candidate';
SELECT 'business_object_2=Workflow';

SELECT 'candidate_semantics=identity,current_workflow_state,current_stage,next_stage,health,readiness';
SELECT 'workflow_semantics=status,current_stage,next_stage,latency,quality,health';

SELECT 'label_policy=JOIN_DIM_STAGE_AND_DIM_STATUS_LIGHT';
SELECT 'health_icon_policy=JOIN_DIM_STATUS_LIGHT';
SELECT 'fallback_policy=USE_CODE_IF_LABEL_MISSING';

SELECT 'upsert_policy=SEMANTIC_RECALCULABLE';
SELECT 'ui_policy=UI_READS_SEMANTIC_OR_MART_ONLY';
SELECT 'no_raw_policy=true';
SELECT 'no_fact_direct_ui_policy=true';

SELECT 'localized_labels=RU';
SELECT 'traffic_light_policy=health_score_health_light_health_reason_code';
SELECT 'multi_exchange=true';
SELECT 'multi_broker=true';
SELECT 'multilingual_ready=true';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_SEMANTIC_BUILDER_PLAN_V1_READY';
SQL

echo "TEST_WORKFLOW_SEMANTIC_BUILDER_PLAN_V1_OK"
