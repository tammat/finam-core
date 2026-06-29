#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_DISCOVERY_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_feature_discovery_validation_v1.py \
  | tee /tmp/feature_discovery_validation_v1.out

grep -q "FEATURE_DISCOVERY_VALIDATION_V1" /tmp/feature_discovery_validation_v1.out
grep -q "domain=FEATURES" /tmp/feature_discovery_validation_v1.out
grep -q "catalog_total=352" /tmp/feature_discovery_validation_v1.out
grep -q "required_fields_valid=352" /tmp/feature_discovery_validation_v1.out
grep -q "duplicate_object_ids=0" /tmp/feature_discovery_validation_v1.out
grep -q "green_objects=352" /tmp/feature_discovery_validation_v1.out
grep -q "feature_profile_valid=1" /tmp/feature_discovery_validation_v1.out
grep -q "runtime_changed=0" /tmp/feature_discovery_validation_v1.out
grep -q "execution_changed=0" /tmp/feature_discovery_validation_v1.out
grep -q "orders_changed=0" /tmp/feature_discovery_validation_v1.out
grep -q "fills_changed=0" /tmp/feature_discovery_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/feature_discovery_validation_v1.out
grep -q "VERDICT=FEATURE_DISCOVERY_VALIDATION_V1_READY" /tmp/feature_discovery_validation_v1.out

echo "TEST_FEATURE_DISCOVERY_VALIDATION_V1_OK"
