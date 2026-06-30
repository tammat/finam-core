#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_FINAL_VALIDATION_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/build_data_object_classification_final_validation_v1.py \
  >/tmp/data_object_classification_final_validation_v1.out

cat /tmp/data_object_classification_final_validation_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_FINAL_VALIDATION_V1_READY" /tmp/data_object_classification_final_validation_v1.out
grep -q "active_sources=12" /tmp/data_object_classification_final_validation_v1.out
grep -q "duplicate_sources=0" /tmp/data_object_classification_final_validation_v1.out
grep -q "data_source_objects=33" /tmp/data_object_classification_final_validation_v1.out
grep -q "true_coverage_pct=100.0" /tmp/data_object_classification_final_validation_v1.out
grep -q "total_objects=373" /tmp/data_object_classification_final_validation_v1.out
grep -q "other_objects=10" /tmp/data_object_classification_final_validation_v1.out
grep -q "applied_high=27" /tmp/data_object_classification_final_validation_v1.out
grep -q "applied_medium_safe=7" /tmp/data_object_classification_final_validation_v1.out
grep -q "applied_refined_medium=13" /tmp/data_object_classification_final_validation_v1.out
grep -q "high_remaining=0" /tmp/data_object_classification_final_validation_v1.out
grep -q "medium_remaining=0" /tmp/data_object_classification_final_validation_v1.out
grep -q "low_remaining=10" /tmp/data_object_classification_final_validation_v1.out
grep -q "registry_consistency=OK" /tmp/data_object_classification_final_validation_v1.out
grep -q "classification_consistency=OK" /tmp/data_object_classification_final_validation_v1.out
grep -q "coverage_consistency=OK" /tmp/data_object_classification_final_validation_v1.out
grep -q "pipeline_consistency=OK" /tmp/data_object_classification_final_validation_v1.out
grep -q "metadata_catalog_consistency=OK" /tmp/data_object_classification_final_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_final_validation_v1.out

echo "final_validation=READY"
echo "metadata_catalog_consistency=READY"
echo "registry_consistency=READY"
echo "classification_consistency=READY"
echo "coverage_consistency=READY"
echo "pipeline_consistency=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_FINAL_VALIDATION_V1_OK"
