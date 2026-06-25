#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_NORMALIZATION_ENGINE_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_normalization_engine_v1.py --save \
  | tee /tmp/workflow_normalization_engine_v1.out

grep -q "WORKFLOW_NORMALIZATION_ENGINE_V1" /tmp/workflow_normalization_engine_v1.out
grep -q "mode=save" /tmp/workflow_normalization_engine_v1.out
grep -q "normalized_event_total=" /tmp/workflow_normalization_engine_v1.out
grep -q "normalized_run_total=" /tmp/workflow_normalization_engine_v1.out
grep -q "broker_id=FINAM" /tmp/workflow_normalization_engine_v1.out
grep -q "exchange_id=MOEX" /tmp/workflow_normalization_engine_v1.out
grep -q "normalization_policy=QUALITY_OK_ONLY" /tmp/workflow_normalization_engine_v1.out
grep -q "canonicalization_ready=1" /tmp/workflow_normalization_engine_v1.out
grep -q "incremental_policy=changed_since_only" /tmp/workflow_normalization_engine_v1.out
grep -q "no_full_scan_policy=1" /tmp/workflow_normalization_engine_v1.out
grep -q "runtime_changed=0" /tmp/workflow_normalization_engine_v1.out
grep -q "execution_changed=0" /tmp/workflow_normalization_engine_v1.out
grep -q "orders_changed=0" /tmp/workflow_normalization_engine_v1.out
grep -q "fills_changed=0" /tmp/workflow_normalization_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_normalization_engine_v1.out
grep -q "VERDICT=WORKFLOW_NORMALIZATION_ENGINE_V1_READY" /tmp/workflow_normalization_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'nrm_event_rows=' || count(*)
FROM warehouse.nrm_workflow_event_v1;

SELECT 'nrm_run_rows=' || count(*)
FROM warehouse.nrm_workflow_run_v1;

SELECT 'nrm_event_canonical=' || count(*)
FROM warehouse.nrm_workflow_event_v1
WHERE broker_id='FINAM'
  AND exchange_id='MOEX'
  AND candidate_id IS NOT NULL
  AND workflow_run_id IS NOT NULL;

SELECT 'nrm_run_latest=' ||
       candidate_id || '|' ||
       broker_id || '|' ||
       exchange_id || '|' ||
       coalesce(market_code,'NULL') || '|' ||
       coalesce(asset_class_code,'NULL') || '|' ||
       status_code || '|' ||
       stage_code
FROM warehouse.nrm_workflow_run_v1
ORDER BY normalized_run_id DESC
LIMIT 1;
SQL

echo "TEST_WORKFLOW_NORMALIZATION_ENGINE_V1_OK"
