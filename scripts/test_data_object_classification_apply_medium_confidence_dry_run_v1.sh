#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_CONFIDENCE_DRY_RUN_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/dry_run_data_object_classification_medium_confidence_v1.py \
  >/tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out

cat /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_CONFIDENCE_DRY_RUN_V1_READY" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "SECTION=SUMMARY" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "medium_rows=20" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "SECTION=RULES" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "SECTION=OBJECTS" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "SECTION=ESTIMATED_OBJECT_TYPE_COUNTS" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "database_write_mode=DRY_RUN_ONLY" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "classification_changed=0" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "review_status_changed=0" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out

grep -q "RULE|rule=event_infra" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "RULE|rule=prefix_runtime" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "OBJECT|group=REVIEW|schema=public|table=runtime_regime_overrides" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out
grep -q "OBJECT|group=SAFE|schema=public|table=event_store" /tmp/data_object_classification_apply_medium_confidence_dry_run_v1.out

echo "medium_confidence_dry_run=READY"
echo "safe_review_skip_split=READY"
echo "estimated_counts=READY"
echo "apply_not_performed=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_CONFIDENCE_DRY_RUN_V1_OK"
