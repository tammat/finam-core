#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_SAFE_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/apply_data_object_classification_medium_safe_v1.py \
  >/tmp/data_object_classification_apply_medium_safe_v1.out

cat /tmp/data_object_classification_apply_medium_safe_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_SAFE_V1_READY" /tmp/data_object_classification_apply_medium_safe_v1.out
grep -q "medium_safe_to_apply=7" /tmp/data_object_classification_apply_medium_safe_v1.out
grep -q "classification_rows_updated=7" /tmp/data_object_classification_apply_medium_safe_v1.out
grep -q "other_after=23" /tmp/data_object_classification_apply_medium_safe_v1.out
grep -q "medium_remaining=13" /tmp/data_object_classification_apply_medium_safe_v1.out
grep -q "low_remaining=10" /tmp/data_object_classification_apply_medium_safe_v1.out
grep -q "review_medium_unsafe_untouched=1" /tmp/data_object_classification_apply_medium_safe_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_apply_medium_safe_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/data_object_classification_apply_medium_safe_db_check_v1.out
SELECT 'event_store=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='event_store';

SELECT 'events=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='events';

SELECT 'profit_lock_events=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='profit_lock_events';

SELECT 'take_profit_events=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='take_profit_events';

SELECT 'clean_paper_accumulation_tracker_v1=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='clean_paper_accumulation_tracker_v1';

SELECT 'runtime_regime_overrides=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='runtime_regime_overrides';

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

cat /tmp/data_object_classification_apply_medium_safe_db_check_v1.out

grep -q "event_store=WORKFLOW" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out
grep -q "events=WORKFLOW" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out
grep -q "profit_lock_events=EXECUTION" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out
grep -q "take_profit_events=EXECUTION" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out
grep -q "clean_paper_accumulation_tracker_v1=ANALYTICS" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out
grep -q "runtime_regime_overrides=OTHER" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out
grep -q "medium_remaining=13" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out
grep -q "low_remaining=10" /tmp/data_object_classification_apply_medium_safe_db_check_v1.out

echo "apply_medium_safe=READY"
echo "medium_review_untouched=READY"
echo "low_untouched=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_SAFE_V1_OK"
