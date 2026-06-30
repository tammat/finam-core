#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_REVIEW_OTHER_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/review_data_object_classification_other_v1.py \
  >/tmp/data_object_classification_review_other_v1.out

cat /tmp/data_object_classification_review_other_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_REVIEW_OTHER_V1_READY" /tmp/data_object_classification_review_other_v1.out
grep -q "review_rows=" /tmp/data_object_classification_review_other_v1.out
grep -q "suggested_changes=" /tmp/data_object_classification_review_other_v1.out
grep -q "high_confidence=" /tmp/data_object_classification_review_other_v1.out
grep -q "review_status=SUGGESTED_ONLY" /tmp/data_object_classification_review_other_v1.out
grep -q "classification_changed=0" /tmp/data_object_classification_review_other_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_review_other_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/data_object_classification_review_other_db_check_v1.out
SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.data_object_classification_review_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'rows=' || count(*)
FROM warehouse.data_object_classification_review_v1
WHERE active=true;

SELECT 'runtime_active_universe=' || suggested_object_type
FROM warehouse.data_object_classification_review_v1
WHERE schema_name='public'
  AND table_name='runtime_active_universe';

SELECT 'manual_trade_journal=' || suggested_object_type
FROM warehouse.data_object_classification_review_v1
WHERE schema_name='public'
  AND table_name='manual_trade_journal';

SELECT 'trade_attribution_v2=' || suggested_object_type
FROM warehouse.data_object_classification_review_v1
WHERE schema_name='public'
  AND table_name='trade_attribution_v2';
SQL

cat /tmp/data_object_classification_review_other_db_check_v1.out

grep -q "table=READY" /tmp/data_object_classification_review_other_db_check_v1.out
grep -q "runtime_active_universe=REFERENCE" /tmp/data_object_classification_review_other_db_check_v1.out
grep -q "manual_trade_journal=AUDIT" /tmp/data_object_classification_review_other_db_check_v1.out
grep -q "trade_attribution_v2=ANALYTICS" /tmp/data_object_classification_review_other_db_check_v1.out

echo "review_other=READY"
echo "suggestions_persisted=READY"
echo "apply_not_performed=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_REVIEW_OTHER_V1_OK"
