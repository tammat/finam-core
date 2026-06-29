#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MODEL_DISCOVERY_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_model_discovery_validation_v1.py \
  | tee /tmp/model_discovery_validation_v1.out

grep -q "MODEL_DISCOVERY_VALIDATION_V1" /tmp/model_discovery_validation_v1.out
grep -q "domain=MODELS" /tmp/model_discovery_validation_v1.out
grep -q "catalog_total=280" /tmp/model_discovery_validation_v1.out
grep -q "required_fields_valid=280" /tmp/model_discovery_validation_v1.out
grep -q "duplicate_object_ids=0" /tmp/model_discovery_validation_v1.out
grep -q "green_objects=280" /tmp/model_discovery_validation_v1.out
grep -q "model_profile_valid=1" /tmp/model_discovery_validation_v1.out
grep -q "ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION" /tmp/model_discovery_validation_v1.out
grep -q "model_policy=MODEL_NO_DIRECT_EXECUTION" /tmp/model_discovery_validation_v1.out
grep -q "runtime_changed=0" /tmp/model_discovery_validation_v1.out
grep -q "execution_changed=0" /tmp/model_discovery_validation_v1.out
grep -q "orders_changed=0" /tmp/model_discovery_validation_v1.out
grep -q "fills_changed=0" /tmp/model_discovery_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/model_discovery_validation_v1.out
grep -q "VERDICT=MODEL_DISCOVERY_VALIDATION_V1_READY" /tmp/model_discovery_validation_v1.out

echo "TEST_MODEL_DISCOVERY_VALIDATION_V1_OK"
