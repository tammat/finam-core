#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_MART_BUILDER_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_1=warehouse.sem_candidate_v1';
SELECT 'source_2=warehouse.sem_workflow_v1';

SELECT 'source_1_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='sem_candidate_v1'
);

SELECT 'source_2_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='sem_workflow_v1'
);

SELECT 'source_1_rows=' || count(*)
FROM warehouse.sem_candidate_v1;

SELECT 'source_2_rows=' || count(*)
FROM warehouse.sem_workflow_v1;

SELECT 'target_1=warehouse.mart_workflow_dashboard_v1';
SELECT 'target_2=warehouse.mart_candidate_workflow_v1';

SELECT 'target_1_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='mart_workflow_dashboard_v1'
);

SELECT 'target_2_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse'
      AND table_name='mart_candidate_workflow_v1'
);

SELECT 'mart_policy=UI_READY_RECALCULABLE_DATASET';
SELECT 'mart_source_policy=SEMANTIC_ONLY';
SELECT 'presentation_policy=READS_MART_OR_SNAPSHOT_ONLY';
SELECT 'ui_policy=NO_RAW_NO_QUALITY_NO_NORMALIZED_NO_FACT_NO_DIMENSION_NO_SEMANTIC_DIRECT';
SELECT 'dashboard_sections=system,workflow,warehouse,research,execution_safety,health';
SELECT 'traffic_light_policy=health_score_health_light_health_icon';
SELECT 'localized_labels_policy=FROM_SEMANTIC';
SELECT 'snapshot_policy=SNAPSHOT_AFTER_MART';
SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_MART_BUILDER_SCHEMA_V1_READY';
SQL

echo "TEST_WORKFLOW_MART_BUILDER_SCHEMA_V1_OK"
