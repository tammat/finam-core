#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_AI_REGISTRY_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_ai_registry_builder_v1.py \
  | tee /tmp/ai_registry_builder_v1.out

grep -q "AI_REGISTRY_BUILDER_V1" /tmp/ai_registry_builder_v1.out
grep -q "ai_registry_total=10" /tmp/ai_registry_builder_v1.out
grep -q "type_count=AI_AGENT:4" /tmp/ai_registry_builder_v1.out
grep -q "type_count=AI_CAPABILITY:2" /tmp/ai_registry_builder_v1.out
grep -q "type_count=AI_POLICY:4" /tmp/ai_registry_builder_v1.out
grep -q "unsafe_ai_rows=0" /tmp/ai_registry_builder_v1.out
grep -q "framework=REGISTRY_FRAMEWORK_V1" /tmp/ai_registry_builder_v1.out
grep -q "bootstrap_policy=AI_BOOTSTRAP_POLICY_V1" /tmp/ai_registry_builder_v1.out
grep -q "discovery_used=0" /tmp/ai_registry_builder_v1.out
grep -q "market_knowledge_stored=0" /tmp/ai_registry_builder_v1.out
grep -q "runtime_changed=0" /tmp/ai_registry_builder_v1.out
grep -q "execution_changed=0" /tmp/ai_registry_builder_v1.out
grep -q "orders_changed=0" /tmp/ai_registry_builder_v1.out
grep -q "fills_changed=0" /tmp/ai_registry_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/ai_registry_builder_v1.out
grep -q "VERDICT=AI_REGISTRY_BUILDER_V1_READY" /tmp/ai_registry_builder_v1.out

echo "TEST_AI_REGISTRY_BUILDER_V1_OK"
