#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_DATA_CONSOLIDATION_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_registry_data_consolidation_builder_v1.py \
  | tee /tmp/registry_data_consolidation_builder_v1.out

grep -q "REGISTRY_DATA_CONSOLIDATION_BUILDER_V1" /tmp/registry_data_consolidation_builder_v1.out
grep -q "relationship_count=CATALOG_TO_FEATURE:352" /tmp/registry_data_consolidation_builder_v1.out
grep -q "relationship_count=CATALOG_TO_MODEL:280" /tmp/registry_data_consolidation_builder_v1.out
grep -q "registry_relationship_total=632" /tmp/registry_data_consolidation_builder_v1.out
grep -q "политика=СВЯЗИ_БЕЗ_КОПИРОВАНИЯ_ДАННЫХ" /tmp/registry_data_consolidation_builder_v1.out
grep -q "runtime_changed=0" /tmp/registry_data_consolidation_builder_v1.out
grep -q "execution_changed=0" /tmp/registry_data_consolidation_builder_v1.out
grep -q "orders_changed=0" /tmp/registry_data_consolidation_builder_v1.out
grep -q "fills_changed=0" /tmp/registry_data_consolidation_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/registry_data_consolidation_builder_v1.out
grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_BUILDER_V1_READY" /tmp/registry_data_consolidation_builder_v1.out

echo "TEST_REGISTRY_DATA_CONSOLIDATION_BUILDER_V1_OK"
