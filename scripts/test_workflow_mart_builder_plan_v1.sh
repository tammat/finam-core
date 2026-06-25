#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_MART_BUILDER_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'planned_source_1=warehouse.sem_candidate_v1';
SELECT 'planned_source_2=warehouse.sem_workflow_v1';

SELECT 'planned_target_1=warehouse.mart_workflow_dashboard_v1';
SELECT 'planned_target_2=warehouse.mart_candidate_workflow_v1';

SELECT 'mart_candidate_fields=candidate_id,workflow_run_id,symbol,display_symbol,strategy_code,timeframe,workflow_status_code,workflow_status_label_ru,current_stage_code,current_stage_label_ru,next_stage_code,next_stage_label_ru,health_score,health_light,health_icon,health_reason_code,mart_version,payload';

SELECT 'mart_dashboard_fields=section_code,section_title_ru,metric_code,metric_label_ru,metric_value,health_score,health_light,health_icon,health_reason_code,mart_version,payload';

SELECT 'dashboard_section_1=system';
SELECT 'dashboard_section_2=workflow';
SELECT 'dashboard_section_3=warehouse';
SELECT 'dashboard_section_4=research';
SELECT 'dashboard_section_5=execution_safety';
SELECT 'dashboard_section_6=health';

SELECT 'mart_policy=UI_READY_RECALCULABLE_DATASET';
SELECT 'source_policy=SEMANTIC_ONLY';
SELECT 'presentation_policy=READS_MART_OR_SNAPSHOT_ONLY';
SELECT 'ui_forbidden_policy=NO_RAW_NO_QUALITY_NO_NORMALIZED_NO_FACT_NO_DIMENSION_NO_SEMANTIC_DIRECT';
SELECT 'localized_labels_policy=FROM_SEMANTIC_OR_MART';
SELECT 'traffic_light_policy=health_score_health_light_health_icon';
SELECT 'upsert_policy=MART_RECALCULABLE';
SELECT 'snapshot_policy=SNAPSHOT_AFTER_MART';

SELECT 'expected_candidate_rows=1';
SELECT 'expected_dashboard_min_rows=6';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_MART_BUILDER_PLAN_V1_READY';
SQL

echo "TEST_WORKFLOW_MART_BUILDER_PLAN_V1_OK"
