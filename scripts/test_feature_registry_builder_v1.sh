#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_REGISTRY_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_feature_registry_builder_v1.py \
  | tee /tmp/feature_registry_builder_v1.out

grep -q "FEATURE_REGISTRY_BUILDER_V1" /tmp/feature_registry_builder_v1.out
grep -q "feature_registry_total=352" /tmp/feature_registry_builder_v1.out
grep -q "status_count=DISCOVERED:352" /tmp/feature_registry_builder_v1.out
grep -q "source_policy=DISCOVERY_TO_REGISTRY" /tmp/feature_registry_builder_v1.out
grep -q "runtime_changed=0" /tmp/feature_registry_builder_v1.out
grep -q "execution_changed=0" /tmp/feature_registry_builder_v1.out
grep -q "orders_changed=0" /tmp/feature_registry_builder_v1.out
grep -q "fills_changed=0" /tmp/feature_registry_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/feature_registry_builder_v1.out
grep -q "VERDICT=FEATURE_REGISTRY_BUILDER_V1_READY" /tmp/feature_registry_builder_v1.out

echo "TEST_FEATURE_REGISTRY_BUILDER_V1_OK"
