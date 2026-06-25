#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STATISTICS_PIPELINE_ENGINE_V1 ==="

PYTHONPATH=src src/scripts/research/build_statistics_pipeline_engine_v1.py --save \
  | tee /tmp/statistics_pipeline_engine_v1.out

grep -q "STATISTICS_PIPELINE_ENGINE_V1" /tmp/statistics_pipeline_engine_v1.out
grep -q "mode=save" /tmp/statistics_pipeline_engine_v1.out
grep -q "inserted_rows=1" /tmp/statistics_pipeline_engine_v1.out
grep -q "pipeline=WORKFLOW_QUALITY_PIPELINE|QUALITY|COMPLETED" /tmp/statistics_pipeline_engine_v1.out
grep -q "pipeline_model=LAYERED_PIPELINE" /tmp/statistics_pipeline_engine_v1.out
grep -q "quality_pipeline_registered=1" /tmp/statistics_pipeline_engine_v1.out
grep -q "monitoring_ready=1" /tmp/statistics_pipeline_engine_v1.out
grep -q "incremental_policy=changed_since_only" /tmp/statistics_pipeline_engine_v1.out
grep -q "no_full_scan_policy=1" /tmp/statistics_pipeline_engine_v1.out
grep -q "runtime_changed=0" /tmp/statistics_pipeline_engine_v1.out
grep -q "execution_changed=0" /tmp/statistics_pipeline_engine_v1.out
grep -q "orders_changed=0" /tmp/statistics_pipeline_engine_v1.out
grep -q "fills_changed=0" /tmp/statistics_pipeline_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/statistics_pipeline_engine_v1.out
grep -q "VERDICT=STATISTICS_PIPELINE_ENGINE_V1_READY" /tmp/statistics_pipeline_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'pipeline_runs=' || count(*)
FROM warehouse.pipeline_runs_v1;

SELECT 'latest_pipeline=' ||
       pipeline_name || '|' ||
       pipeline_layer || '|' ||
       pipeline_status || '|' ||
       health_light || '|' ||
       health_reason_code
FROM warehouse.pipeline_runs_v1
ORDER BY pipeline_run_id DESC
LIMIT 1;
SQL

echo "TEST_STATISTICS_PIPELINE_ENGINE_V1_OK"
