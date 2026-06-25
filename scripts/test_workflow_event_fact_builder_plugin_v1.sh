#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_event_fact_builder_plugin_v1.py --save \
  | tee /tmp/workflow_event_fact_builder_plugin_v1.out

grep -q "WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "mode=save" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "result_status=COMPLETED" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "result_reason=WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_OK" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "stage_facts_total=6" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "health_light=GREEN" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "builder_model=PLUGIN_BASED" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "fact_policy=STORE_CODES_ONLY" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "runtime_changed=0" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "execution_changed=0" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "orders_changed=0" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "fills_changed=0" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_event_fact_builder_plugin_v1.out
grep -q "VERDICT=WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1_READY" /tmp/workflow_event_fact_builder_plugin_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'stage_facts=' || count(*)
FROM warehouse.fact_event_workflow_stage_v1;

SELECT 'transition_facts=' || count(*)
FROM warehouse.fact_event_workflow_transition_v1;

SELECT 'latest_fact_pipeline=' ||
       pipeline_status || '|' ||
       rows_out || '|' ||
       health_light || '|' ||
       health_reason_code
FROM warehouse.fact_pipeline_runs_v1
WHERE builder_name='WORKFLOW_EVENT_FACT_BUILDER_V1'
ORDER BY fact_pipeline_run_id DESC
LIMIT 1;
SQL

echo "TEST_WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1_OK"
