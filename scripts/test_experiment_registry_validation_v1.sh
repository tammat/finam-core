#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPERIMENT_REGISTRY_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_experiment_registry_validation_v1.py \
  | tee /tmp/experiment_registry_validation_v1.out

grep -q "EXPERIMENT_REGISTRY_VALIDATION_V1" /tmp/experiment_registry_validation_v1.out
grep -q "experiment_registry_total=1" /tmp/experiment_registry_validation_v1.out
grep -q "required_fields_valid=1" /tmp/experiment_registry_validation_v1.out
grep -q "duplicate_experiment_codes=0" /tmp/experiment_registry_validation_v1.out
grep -q "unsafe_approvals=0" /tmp/experiment_registry_validation_v1.out
grep -q "experiment_registry_valid=1" /tmp/experiment_registry_validation_v1.out
grep -q "runtime_changed=0" /tmp/experiment_registry_validation_v1.out
grep -q "execution_changed=0" /tmp/experiment_registry_validation_v1.out
grep -q "orders_changed=0" /tmp/experiment_registry_validation_v1.out
grep -q "fills_changed=0" /tmp/experiment_registry_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/experiment_registry_validation_v1.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_VALIDATION_V1_READY" /tmp/experiment_registry_validation_v1.out

echo "TEST_EXPERIMENT_REGISTRY_VALIDATION_V1_OK"
