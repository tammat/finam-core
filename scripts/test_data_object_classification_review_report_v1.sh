#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_REVIEW_REPORT_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/build_data_object_classification_review_report_v1.py \
  >/tmp/data_object_classification_review_report_v1.out

cat /tmp/data_object_classification_review_report_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_REVIEW_REPORT_V1_READY" /tmp/data_object_classification_review_report_v1.out
grep -q "SECTION=SUMMARY" /tmp/data_object_classification_review_report_v1.out
grep -q "tables_total=373" /tmp/data_object_classification_review_report_v1.out
grep -q "before_other=57" /tmp/data_object_classification_review_report_v1.out
grep -q "after_high_apply=30" /tmp/data_object_classification_review_report_v1.out
grep -q "high_applied=27" /tmp/data_object_classification_review_report_v1.out
grep -q "medium_pending=20" /tmp/data_object_classification_review_report_v1.out
grep -q "low_pending=10" /tmp/data_object_classification_review_report_v1.out
grep -q "other_reduction=27" /tmp/data_object_classification_review_report_v1.out
grep -q "reduction_pct=47.37" /tmp/data_object_classification_review_report_v1.out
grep -q "SECTION=OBJECT_TYPE_COUNTS" /tmp/data_object_classification_review_report_v1.out
grep -q "SECTION=APPLIED_RULES" /tmp/data_object_classification_review_report_v1.out
grep -q "high_remaining=0" /tmp/data_object_classification_review_report_v1.out
grep -q "classification_consistency=OK" /tmp/data_object_classification_review_report_v1.out
grep -q "medium_phase=PENDING" /tmp/data_object_classification_review_report_v1.out
grep -q "low_phase=PENDING" /tmp/data_object_classification_review_report_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_review_report_v1.out

echo "review_report=READY"
echo "high_phase_reported=READY"
echo "medium_pending_reported=READY"
echo "low_pending_reported=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_REVIEW_REPORT_V1_OK"
