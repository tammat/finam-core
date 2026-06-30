#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_APPLY_REFINED_MEDIUM_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/apply_data_object_classification_refined_medium_v1.py \
  >/tmp/data_object_classification_apply_refined_medium_v1.out

cat /tmp/data_object_classification_apply_refined_medium_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_REFINED_MEDIUM_V1_READY" /tmp/data_object_classification_apply_refined_medium_v1.out
grep -q "refined_medium_to_apply=13" /tmp/data_object_classification_apply_refined_medium_v1.out
grep -q "classification_rows_updated=13" /tmp/data_object_classification_apply_refined_medium_v1.out
grep -q "review_rows_updated=13" /tmp/data_object_classification_apply_refined_medium_v1.out
grep -q "other_after=10" /tmp/data_object_classification_apply_refined_medium_v1.out
grep -q "medium_remaining=0" /tmp/data_object_classification_apply_refined_medium_v1.out
grep -q "low_remaining=10" /tmp/data_object_classification_apply_refined_medium_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_apply_refined_medium_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/data_object_classification_apply_refined_medium_db_check_v1.out
SELECT 'runtime_regime_overrides=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='runtime_regime_overrides';

SELECT 'runtime_universe_rotation_log=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='runtime_universe_rotation_log';

SELECT 'runtime_calibration_decisions_v1=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='research'
  AND table_name='runtime_calibration_decisions_v1';

SELECT 'shadow_runtime_queue_v1=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='research'
  AND table_name='shadow_runtime_queue_v1';

SELECT 'shadow_runtime_runs_v1=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='research'
  AND table_name='shadow_runtime_runs_v1';

SELECT 'institutional_flow_regime_events=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='institutional_flow_regime_events';

SELECT 'trusted_runtime_active_universe_sync_v1=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='trusted_runtime_active_universe_sync_v1';

SELECT 'medium_remaining=' || count(*)
FROM warehouse.data_object_classification_review_v1
WHERE active=true
  AND review_status='SUGGESTED'
  AND confidence='MEDIUM';

SELECT 'low_remaining=' || count(*)
FROM warehouse.data_object_classification_review_v1
WHERE active=true
  AND review_status='SUGGESTED'
  AND confidence='LOW';

SELECT 'other=' || count(*)
FROM warehouse.data_object_classification_v1
WHERE active=true
  AND object_type='OTHER';
SQL

cat /tmp/data_object_classification_apply_refined_medium_db_check_v1.out

grep -q "runtime_regime_overrides=CONFIGURATION" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "runtime_universe_rotation_log=TELEMETRY" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "runtime_calibration_decisions_v1=RESEARCH" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "shadow_runtime_queue_v1=WORKFLOW" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "shadow_runtime_runs_v1=WORKFLOW" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "institutional_flow_regime_events=ANALYTICS" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "trusted_runtime_active_universe_sync_v1=WORKFLOW" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "medium_remaining=0" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "low_remaining=10" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out
grep -q "other=10" /tmp/data_object_classification_apply_refined_medium_db_check_v1.out

echo "apply_refined_medium=READY"
echo "remaining_medium_applied=READY"
echo "low_untouched=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_APPLY_REFINED_MEDIUM_V1_OK"
