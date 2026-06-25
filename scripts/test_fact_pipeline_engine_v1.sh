#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FACT_PIPELINE_ENGINE_V1 ==="

PYTHONPATH=src src/scripts/research/build_fact_pipeline_engine_v1.py --save \
  | tee /tmp/fact_pipeline_engine_v1.out

grep -q "FACT_PIPELINE_ENGINE_V1" /tmp/fact_pipeline_engine_v1.out
grep -q "mode=save" /tmp/fact_pipeline_engine_v1.out
grep -q "inserted_rows=1" /tmp/fact_pipeline_engine_v1.out
grep -q "fact_pipeline=WORKFLOW_EVENT_FACT_PIPELINE|WORKFLOW|EVENT_FACT|WORKFLOW_EVENT_FACT_BUILDER_V1|PLANNED" /tmp/fact_pipeline_engine_v1.out
grep -q "pipeline_model=BUILDER_BASED_FACT_PIPELINE" /tmp/fact_pipeline_engine_v1.out
grep -q "event_fact_builder_registered=1" /tmp/fact_pipeline_engine_v1.out
grep -q "state_fact_builder_deferred=1" /tmp/fact_pipeline_engine_v1.out
grep -q "workflow_domain_first=1" /tmp/fact_pipeline_engine_v1.out
grep -q "market_trade_edge_deferred=1" /tmp/fact_pipeline_engine_v1.out
grep -q "incremental_policy=changed_since_only" /tmp/fact_pipeline_engine_v1.out
grep -q "no_full_scan_policy=1" /tmp/fact_pipeline_engine_v1.out
grep -q "runtime_changed=0" /tmp/fact_pipeline_engine_v1.out
grep -q "execution_changed=0" /tmp/fact_pipeline_engine_v1.out
grep -q "orders_changed=0" /tmp/fact_pipeline_engine_v1.out
grep -q "fills_changed=0" /tmp/fact_pipeline_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/fact_pipeline_engine_v1.out
grep -q "VERDICT=FACT_PIPELINE_ENGINE_V1_READY" /tmp/fact_pipeline_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'fact_pipeline_runs=' || count(*)
FROM warehouse.fact_pipeline_runs_v1;

SELECT 'latest_fact_pipeline=' ||
       pipeline_name || '|' ||
       fact_domain || '|' ||
       fact_type || '|' ||
       builder_name || '|' ||
       pipeline_status || '|' ||
       health_light || '|' ||
       health_reason_code
FROM warehouse.fact_pipeline_runs_v1
ORDER BY fact_pipeline_run_id DESC
LIMIT 1;
SQL

echo "TEST_FACT_PIPELINE_ENGINE_V1_OK"
