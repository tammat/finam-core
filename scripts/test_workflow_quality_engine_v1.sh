#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_QUALITY_ENGINE_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_quality_engine_v1.py --save \
  | tee /tmp/workflow_quality_engine_v1.out

grep -q "WORKFLOW_QUALITY_ENGINE_V1" /tmp/workflow_quality_engine_v1.out
grep -q "mode=save" /tmp/workflow_quality_engine_v1.out
grep -q "event_quality_total=" /tmp/workflow_quality_engine_v1.out
grep -q "run_quality_total=" /tmp/workflow_quality_engine_v1.out
grep -q "incremental_policy=changed_since_only" /tmp/workflow_quality_engine_v1.out
grep -q "no_full_scan_policy=1" /tmp/workflow_quality_engine_v1.out
grep -q "runtime_changed=0" /tmp/workflow_quality_engine_v1.out
grep -q "execution_changed=0" /tmp/workflow_quality_engine_v1.out
grep -q "orders_changed=0" /tmp/workflow_quality_engine_v1.out
grep -q "fills_changed=0" /tmp/workflow_quality_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_quality_engine_v1.out
grep -q "VERDICT=WORKFLOW_QUALITY_ENGINE_V1_READY" /tmp/workflow_quality_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'qlt_event_rows=' || count(*)
FROM warehouse.qlt_workflow_event_v1;

SELECT 'qlt_run_rows=' || count(*)
FROM warehouse.qlt_workflow_run_v1;

SELECT 'qlt_event_statuses=' ||
       string_agg(quality_status || ':' || cnt, ',' ORDER BY quality_status)
FROM (
    SELECT quality_status, count(*) AS cnt
    FROM warehouse.qlt_workflow_event_v1
    GROUP BY quality_status
) s;

SELECT 'qlt_run_statuses=' ||
       string_agg(quality_status || ':' || cnt, ',' ORDER BY quality_status)
FROM (
    SELECT quality_status, count(*) AS cnt
    FROM warehouse.qlt_workflow_run_v1
    GROUP BY quality_status
) s;
SQL

echo "TEST_WORKFLOW_QUALITY_ENGINE_V1_OK"
