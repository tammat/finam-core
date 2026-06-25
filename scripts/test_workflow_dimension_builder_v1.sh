#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_DIMENSION_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_dimension_builder_v1.py --save \
  | tee /tmp/workflow_dimension_builder_v1.out

grep -q "WORKFLOW_DIMENSION_BUILDER_V1" /tmp/workflow_dimension_builder_v1.out
grep -q "mode=save" /tmp/workflow_dimension_builder_v1.out
grep -q "dim_stage_total=8" /tmp/workflow_dimension_builder_v1.out
grep -q "dim_status_light_total=7" /tmp/workflow_dimension_builder_v1.out
grep -q "dim_stage_risk=RISK" /tmp/workflow_dimension_builder_v1.out
grep -q "dim_light_green=GREEN" /tmp/workflow_dimension_builder_v1.out
grep -q "dimension_policy=REFERENCE_ENRICHED_LOOKUPS" /tmp/workflow_dimension_builder_v1.out
grep -q "localization_policy=RU_LABELS_FROM_REFERENCE" /tmp/workflow_dimension_builder_v1.out
grep -q "fallback_policy=USE_CODE_IF_LABEL_MISSING" /tmp/workflow_dimension_builder_v1.out
grep -q "fact_policy=FACTS_STORE_CODES_ONLY" /tmp/workflow_dimension_builder_v1.out
grep -q "mart_policy=MART_USES_DIMENSIONS_FOR_LABELS" /tmp/workflow_dimension_builder_v1.out
grep -q "runtime_changed=0" /tmp/workflow_dimension_builder_v1.out
grep -q "execution_changed=0" /tmp/workflow_dimension_builder_v1.out
grep -q "orders_changed=0" /tmp/workflow_dimension_builder_v1.out
grep -q "fills_changed=0" /tmp/workflow_dimension_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_dimension_builder_v1.out
grep -q "VERDICT=WORKFLOW_DIMENSION_BUILDER_V1_READY" /tmp/workflow_dimension_builder_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'dim_stage_rows=' || count(*)
FROM warehouse.dim_stage_v1;

SELECT 'dim_status_light_rows=' || count(*)
FROM warehouse.dim_status_light_v1;

SELECT 'dim_stage_labels=' ||
       string_agg(stage_code || ':' || label_ru, ',' ORDER BY stage_order)
FROM warehouse.dim_stage_v1;

SELECT 'dim_lights=' ||
       string_agg(light_code || ':' || icon, ',' ORDER BY priority)
FROM warehouse.dim_status_light_v1;
SQL

echo "TEST_WORKFLOW_DIMENSION_BUILDER_V1_OK"
