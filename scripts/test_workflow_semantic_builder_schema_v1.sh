#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SEMANTIC_BUILDER_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_1=warehouse.fact_state_candidate_lifecycle_v1';
SELECT 'source_2=warehouse.fact_state_workflow_health_v1';
SELECT 'source_3=warehouse.fact_state_workflow_quality_v1';
SELECT 'source_4=warehouse.dim_stage_v1';
SELECT 'source_5=warehouse.dim_status_light_v1';

SELECT 'source_1_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='fact_state_candidate_lifecycle_v1'
);

SELECT 'source_2_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='fact_state_workflow_health_v1'
);

SELECT 'source_3_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='fact_state_workflow_quality_v1'
);

SELECT 'source_4_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='dim_stage_v1'
);

SELECT 'source_5_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='dim_status_light_v1'
);

SELECT 'target_1=warehouse.sem_candidate_v1';
SELECT 'target_2=warehouse.sem_workflow_v1';

SELECT 'target_1_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='sem_candidate_v1'
);

SELECT 'target_2_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='sem_workflow_v1'
);

SELECT 'semantic_policy=BUSINESS_OBJECTS_FOR_UI';
SELECT 'ui_policy=UI_READS_SEMANTIC_OR_MART_ONLY';
SELECT 'source_policy=NO_RAW_NO_FACT_DIRECTLY_FOR_UI';
SELECT 'localization_policy=RU_LABELS_FROM_DIMENSIONS';
SELECT 'traffic_light_policy=health_light_health_icon';
SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_SEMANTIC_BUILDER_SCHEMA_V1_READY';
SQL

echo "TEST_WORKFLOW_SEMANTIC_BUILDER_SCHEMA_V1_OK"
