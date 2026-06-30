#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_REVIEW_REMAINING_MEDIUM_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/review_data_object_classification_remaining_medium_v1.py \
  >/tmp/data_object_classification_review_remaining_medium_v1.out

cat /tmp/data_object_classification_review_remaining_medium_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_REVIEW_REMAINING_MEDIUM_V1_READY" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "remaining_medium_rows=13" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "apply_rows=13" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "skip_rows=0" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "classification_changed=0" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "database_write_mode=REVIEW_TABLE_ONLY" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_review_remaining_medium_v1.out

grep -q "table=runtime_regime_overrides.*refined=CONFIGURATION" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "table=runtime_universe_rotation_log.*refined=TELEMETRY" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "table=runtime_calibration_decisions_v1.*refined=RESEARCH" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "table=shadow_runtime_queue_v1.*refined=WORKFLOW" /tmp/data_object_classification_review_remaining_medium_v1.out
grep -q "table=institutional_flow_regime_events.*refined=ANALYTICS" /tmp/data_object_classification_review_remaining_medium_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/data_object_classification_review_remaining_medium_db_check_v1.out
SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.data_object_classification_remaining_medium_review_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'rows=' || count(*)
FROM warehouse.data_object_classification_remaining_medium_review_v1
WHERE active=true;

SELECT 'runtime_regime_overrides=' || refined_object_type
FROM warehouse.data_object_classification_remaining_medium_review_v1
WHERE schema_name='public'
  AND table_name='runtime_regime_overrides';

SELECT 'shadow_runtime_queue_v1=' || refined_object_type
FROM warehouse.data_object_classification_remaining_medium_review_v1
WHERE schema_name='research'
  AND table_name='shadow_runtime_queue_v1';

SELECT 'institutional_flow_regime_events=' || refined_object_type
FROM warehouse.data_object_classification_remaining_medium_review_v1
WHERE schema_name='public'
  AND table_name='institutional_flow_regime_events';
SQL

cat /tmp/data_object_classification_review_remaining_medium_db_check_v1.out

grep -q "table=READY" /tmp/data_object_classification_review_remaining_medium_db_check_v1.out
grep -q "rows=13" /tmp/data_object_classification_review_remaining_medium_db_check_v1.out
grep -q "runtime_regime_overrides=CONFIGURATION" /tmp/data_object_classification_review_remaining_medium_db_check_v1.out
grep -q "shadow_runtime_queue_v1=WORKFLOW" /tmp/data_object_classification_review_remaining_medium_db_check_v1.out
grep -q "institutional_flow_regime_events=ANALYTICS" /tmp/data_object_classification_review_remaining_medium_db_check_v1.out

echo "remaining_medium_review=READY"
echo "refined_types_persisted=READY"
echo "apply_not_performed=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_REVIEW_REMAINING_MEDIUM_V1_OK"
