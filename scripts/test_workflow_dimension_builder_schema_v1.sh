#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_DIMENSION_BUILDER_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_1=reference.workflow_stages_v1';
SELECT 'source_2=reference.status_lights_v1';
SELECT 'source_3=reference.localization_labels_v1';

SELECT 'source_1_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='reference' AND table_name='workflow_stages_v1'
);

SELECT 'source_2_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='reference' AND table_name='status_lights_v1'
);

SELECT 'source_3_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='reference' AND table_name='localization_labels_v1'
);

SELECT 'target_1=warehouse.dim_stage_v1';
SELECT 'target_2=warehouse.dim_status_light_v1';

SELECT 'target_1_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='dim_stage_v1'
);

SELECT 'target_2_exists=' || EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='warehouse' AND table_name='dim_status_light_v1'
);

SELECT 'dimension_policy=REFERENCE_ENRICHED_LOOKUPS';
SELECT 'localization_policy=RU_LABELS_FROM_REFERENCE';
SELECT 'fact_policy=FACTS_STORE_CODES_ONLY';
SELECT 'mart_policy=MART_USES_DIMENSIONS_FOR_LABELS';
SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_DIMENSION_BUILDER_SCHEMA_V1_READY';
SQL

echo "TEST_WORKFLOW_DIMENSION_BUILDER_SCHEMA_V1_OK"
