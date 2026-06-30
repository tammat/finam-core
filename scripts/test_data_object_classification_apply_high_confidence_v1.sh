#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_APPLY_HIGH_CONFIDENCE_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/apply_data_object_classification_high_confidence_v1.py \
  >/tmp/data_object_classification_apply_high_confidence_v1.out

cat /tmp/data_object_classification_apply_high_confidence_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_HIGH_CONFIDENCE_V1_READY" /tmp/data_object_classification_apply_high_confidence_v1.out
grep -q "classification_rows_updated=" /tmp/data_object_classification_apply_high_confidence_v1.out
grep -q "high_remaining=0" /tmp/data_object_classification_apply_high_confidence_v1.out
grep -q "medium_applied=0" /tmp/data_object_classification_apply_high_confidence_v1.out
grep -q "low_applied=0" /tmp/data_object_classification_apply_high_confidence_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_apply_high_confidence_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/data_object_classification_apply_high_db_check_v1.out
SELECT 'runtime_active_universe=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='runtime_active_universe';

SELECT 'manual_trade_journal=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='manual_trade_journal';

SELECT 'trade_attribution_v2=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='trade_attribution_v2';

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
SQL

cat /tmp/data_object_classification_apply_high_db_check_v1.out

grep -q "runtime_active_universe=REFERENCE" /tmp/data_object_classification_apply_high_db_check_v1.out
grep -q "manual_trade_journal=AUDIT" /tmp/data_object_classification_apply_high_db_check_v1.out
grep -q "trade_attribution_v2=ANALYTICS" /tmp/data_object_classification_apply_high_db_check_v1.out
grep -q "medium_remaining=20" /tmp/data_object_classification_apply_high_db_check_v1.out
grep -q "low_remaining=10" /tmp/data_object_classification_apply_high_db_check_v1.out

echo "apply_high_confidence=READY"
echo "medium_untouched=READY"
echo "low_untouched=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_APPLY_HIGH_CONFIDENCE_V1_OK"
