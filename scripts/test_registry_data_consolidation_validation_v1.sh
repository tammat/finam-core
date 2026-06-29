#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_registry_data_consolidation_validation_v1.py \
  | tee /tmp/registry_data_consolidation_validation_v1.out

grep -q "REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1" /tmp/registry_data_consolidation_validation_v1.out
grep -q "registry_relationship_total=632" /tmp/registry_data_consolidation_validation_v1.out
grep -q "required_fields_valid=632" /tmp/registry_data_consolidation_validation_v1.out
grep -q "duplicate_relationships=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "not_validated_relationships=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "broken_feature_links=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "broken_model_links=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "registry_relationship_valid=1" /tmp/registry_data_consolidation_validation_v1.out
grep -q "runtime_changed=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "execution_changed=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "orders_changed=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "fills_changed=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/registry_data_consolidation_validation_v1.out
grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1_READY" /tmp/registry_data_consolidation_validation_v1.out

echo "TEST_REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1_OK"
