#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_state_fact_builder_plugin_v1.py --save \
  | tee /tmp/workflow_state_fact_builder_plugin_v1.out

grep -q "WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "mode=save" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "result_status=COMPLETED" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "result_reason=WORKFLOW_STATE_FACT_BUILDER_PLUGIN_OK" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "candidate_lifecycle_total=1" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "workflow_health_total=1" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "workflow_quality_total=1" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "candidate_state=MSC-000001" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "builder_model=PLUGIN_BASED" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "source_policy=NORMALIZED_LAYER_ONLY" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "fact_policy=STATE_FACT_RECALCULABLE" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "runtime_changed=0" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "execution_changed=0" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "orders_changed=0" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "fills_changed=0" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_state_fact_builder_plugin_v1.out
grep -q "VERDICT=WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1_READY" /tmp/workflow_state_fact_builder_plugin_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'candidate_lifecycle=' || count(*)
FROM warehouse.fact_state_candidate_lifecycle_v1;

SELECT 'workflow_health=' || count(*)
FROM warehouse.fact_state_workflow_health_v1;

SELECT 'workflow_quality=' || count(*)
FROM warehouse.fact_state_workflow_quality_v1;

SELECT 'candidate_state_latest=' ||
       candidate_id || '|' ||
       workflow_status_code || '|' ||
       current_stage_code || '|' ||
       coalesce(next_stage_code,'NULL') || '|' ||
       health_light || '|' ||
       health_reason_code
FROM warehouse.fact_state_candidate_lifecycle_v1
ORDER BY updated_at DESC
LIMIT 1;
SQL

echo "TEST_WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1_OK"
