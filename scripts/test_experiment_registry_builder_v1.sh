#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPERIMENT_REGISTRY_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_experiment_registry_builder_v1.py \
  | tee /tmp/experiment_registry_builder_v1.out

grep -q "EXPERIMENT_REGISTRY_BUILDER_V1" /tmp/experiment_registry_builder_v1.out
grep -q "experiment_registry_total=1" /tmp/experiment_registry_builder_v1.out
grep -q "status_count=REGISTERED:1" /tmp/experiment_registry_builder_v1.out
grep -q "политика_источника=RESEARCH_TO_REGISTRY" /tmp/experiment_registry_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/experiment_registry_builder_v1.out
grep -q "runtime_changed=0" /tmp/experiment_registry_builder_v1.out
grep -q "execution_changed=0" /tmp/experiment_registry_builder_v1.out
grep -q "orders_changed=0" /tmp/experiment_registry_builder_v1.out
grep -q "fills_changed=0" /tmp/experiment_registry_builder_v1.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_BUILDER_V1_READY" /tmp/experiment_registry_builder_v1.out

echo "TEST_EXPERIMENT_REGISTRY_BUILDER_V1_OK"
