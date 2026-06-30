#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MODEL_REGISTRY_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_model_registry_builder_v1.py \
  | tee /tmp/model_registry_builder_v1.out

grep -q "MODEL_REGISTRY_BUILDER_V1" /tmp/model_registry_builder_v1.out
grep -q "model_registry_total=280" /tmp/model_registry_builder_v1.out
grep -q "status_count=DISCOVERED:280" /tmp/model_registry_builder_v1.out
grep -q "source_policy=DISCOVERY_TO_REGISTRY" /tmp/model_registry_builder_v1.out
grep -q "ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION" /tmp/model_registry_builder_v1.out
grep -q "model_policy=MODEL_NO_DIRECT_EXECUTION" /tmp/model_registry_builder_v1.out
grep -q "runtime_changed=0" /tmp/model_registry_builder_v1.out
grep -q "execution_changed=0" /tmp/model_registry_builder_v1.out
grep -q "orders_changed=0" /tmp/model_registry_builder_v1.out
grep -q "fills_changed=0" /tmp/model_registry_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/model_registry_builder_v1.out
grep -q "VERDICT=MODEL_REGISTRY_BUILDER_V1_READY" /tmp/model_registry_builder_v1.out

echo "TEST_MODEL_REGISTRY_BUILDER_V1_OK"
