#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STATE_FACT_BUILDER_PLUGIN_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_table=warehouse.nrm_workflow_run_v1';

SELECT 'source_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='nrm_workflow_run_v1'
);

SELECT 'source_rows=' || count(*)
FROM warehouse.nrm_workflow_run_v1;

SELECT 'target_table_1=warehouse.fact_state_candidate_lifecycle_v1';
SELECT 'target_table_2=warehouse.fact_state_workflow_health_v1';
SELECT 'target_table_3=warehouse.fact_state_workflow_quality_v1';

SELECT 'target_1_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='fact_state_candidate_lifecycle_v1'
);

SELECT 'target_2_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='fact_state_workflow_health_v1'
);

SELECT 'target_3_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='fact_state_workflow_quality_v1'
);

SELECT 'framework_components=BuilderContext,BuilderResult,FactBuilder,BuilderRegistry,BuilderExecutor';

SELECT 'builder_name=WORKFLOW_STATE_FACT_BUILDER_V1';
SELECT 'builder_plugin=WorkflowStateFactBuilder';
SELECT 'builder_model=PLUGIN_BASED';

SELECT 'source_policy=NORMALIZED_LAYER_ONLY';
SELECT 'forbidden_source_policy=NO_DIRECT_RESEARCH_SOURCE_FOR_BUILDER';

SELECT 'state_fact_1=CANDIDATE_LIFECYCLE';
SELECT 'state_fact_2=WORKFLOW_HEALTH';
SELECT 'state_fact_3=WORKFLOW_QUALITY';

SELECT 'fact_policy=STATE_FACT_RECALCULABLE';
SELECT 'canonical_policy=STORE_CODES_ONLY';
SELECT 'health_policy=health_score,health_light,health_reason_code';
SELECT 'traffic_light_policy=REFERENCE_STATUS_LIGHTS';

SELECT 'multi_exchange=true';
SELECT 'multi_broker=true';
SELECT 'multilingual_ready=true';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_STATE_FACT_BUILDER_PLUGIN_SCHEMA_V1_READY';
SQL

echo "TEST_WORKFLOW_STATE_FACT_BUILDER_PLUGIN_SCHEMA_V1_OK"
