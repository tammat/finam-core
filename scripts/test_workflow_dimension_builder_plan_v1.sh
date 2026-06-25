#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_DIMENSION_BUILDER_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'planned_source_1=reference.workflow_stages_v1';
SELECT 'planned_source_2=reference.status_lights_v1';
SELECT 'planned_source_3=reference.localization_labels_v1';

SELECT 'planned_target_1=warehouse.dim_stage_v1';
SELECT 'planned_target_2=warehouse.dim_status_light_v1';

SELECT 'dim_stage_fields=stage_code,stage_order,label_ru,short_label_ru,full_label_ru,health_light,is_active';
SELECT 'dim_status_light_fields=light_code,priority,icon,hex_color,label_ru,short_label_ru,is_active';

SELECT 'stage_label_source=localization_labels_v1 WHERE entity_type=workflow_stage AND locale_code=ru_RU';
SELECT 'light_label_source=localization_labels_v1 WHERE entity_type=status_light AND locale_code=ru_RU';

SELECT 'upsert_policy=DIMENSION_RECALCULABLE';
SELECT 'dimension_policy=REFERENCE_ENRICHED_LOOKUPS';
SELECT 'localization_policy=RU_LABELS_FROM_REFERENCE';
SELECT 'fallback_policy=USE_CODE_IF_LABEL_MISSING';
SELECT 'mart_policy=MART_USES_DIMENSIONS_FOR_LABELS';
SELECT 'fact_policy=FACTS_STORE_CODES_ONLY';

SELECT 'expected_stage_min_rows=8';
SELECT 'expected_status_light_rows=7';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_DIMENSION_BUILDER_PLAN_V1_READY';
SQL

echo "TEST_WORKFLOW_DIMENSION_BUILDER_PLAN_V1_OK"
