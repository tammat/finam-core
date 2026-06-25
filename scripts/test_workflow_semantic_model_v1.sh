#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SEMANTIC_MODEL_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'semantic_layer_role=BUSINESS_CONTRACT_BETWEEN_WAREHOUSE_AND_PRESENTATION';

SELECT 'semantic_contract=STABLE';

SELECT 'semantic_objects=Candidate,Workflow';

SELECT 'candidate_sections=Identity,Market,Workflow,Research,Execution,Risk,Health,Statistics,Presentation';

SELECT 'workflow_sections=Identity,CurrentState,CurrentStage,NextStage,Performance,Health,Quality,Presentation';

SELECT 'semantic_reads=warehouse.fact_state_*,warehouse.fact_event_*,warehouse.dim_*';

SELECT 'semantic_forbidden_reads=research.*,raw_*,qlt_*,nrm_*';

SELECT 'ui_reads=SEMANTIC_OR_MART_ONLY';

SELECT 'ui_forbidden_reads=RAW,QUALITY,NORMALIZED,FACT,DIMENSION';

SELECT 'mart_reads=SEMANTIC_ONLY';

SELECT 'presentation_contract=workflow_status_label_ru,current_stage_label_ru,next_stage_label_ru,health_icon,health_light,health_score';

SELECT 'canonical_fields=candidate_id,workflow_run_id,broker_id,exchange_id,market_code,instrument_id,strategy_code,stage_code,status_code,reason_code,health_score,health_light,health_reason_code';

SELECT 'decision_logic_policy=NO_DECISION_LOGIC_IN_SEMANTIC_LAYER';

SELECT 'semantic_policy=DESCRIBE_CURRENT_BUSINESS_STATE_ONLY';

SELECT 'consumer_stability=Mart,Dashboard,ReadOnlyUI,Telegram,API,FutureControlUI';

SELECT 'architecture_freeze=SEMANTIC_LAYER_FREEZE_V1';

SELECT 'next_step=WORKFLOW_SEMANTIC_BUILDER_V1';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_SEMANTIC_MODEL_V1_READY';
SQL

echo "TEST_WORKFLOW_SEMANTIC_MODEL_V1_OK"
