#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_AI_REGISTRY_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_ai_registry_validation_v1.py \
  | tee /tmp/ai_registry_validation_v1.out

grep -q "AI_REGISTRY_VALIDATION_V1" /tmp/ai_registry_validation_v1.out
grep -q "ai_registry_total=10" /tmp/ai_registry_validation_v1.out
grep -q "required_fields_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "duplicate_ai_codes=0" /tmp/ai_registry_validation_v1.out
grep -q "status_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "maturity_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "execution_policy_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "market_policy_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "graph_required_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "bootstrap_policy_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "framework_version_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "domain_types_version_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "description_valid=10" /tmp/ai_registry_validation_v1.out
grep -q "forbidden_market_fields=0" /tmp/ai_registry_validation_v1.out
grep -q "unsafe_live_rows=0" /tmp/ai_registry_validation_v1.out
grep -q "framework=REGISTRY_FRAMEWORK_V1" /tmp/ai_registry_validation_v1.out
grep -q "ai_policy=AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY" /tmp/ai_registry_validation_v1.out
grep -q "runtime_changed=0" /tmp/ai_registry_validation_v1.out
grep -q "execution_changed=0" /tmp/ai_registry_validation_v1.out
grep -q "orders_changed=0" /tmp/ai_registry_validation_v1.out
grep -q "fills_changed=0" /tmp/ai_registry_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/ai_registry_validation_v1.out
grep -q "VERDICT=AI_REGISTRY_VALIDATION_V1_READY" /tmp/ai_registry_validation_v1.out

echo "TEST_AI_REGISTRY_VALIDATION_V1_OK"
