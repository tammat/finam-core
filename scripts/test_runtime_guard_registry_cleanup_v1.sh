#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "TEST_RUNTIME_GUARD_REGISTRY_CLEANUP_V1_START"

python -m py_compile \
  src/scripts/analytics/cleanup_runtime_guard_registry_v1.py

python src/scripts/analytics/cleanup_runtime_guard_registry_v1.py --dry-run \
  | tee /tmp/runtime_guard_registry_cleanup_v1.log

grep -q "RUNTIME_GUARD_REGISTRY_CLEANUP_V1_DRY_RUN" \
  /tmp/runtime_guard_registry_cleanup_v1.log

echo "TEST_RUNTIME_GUARD_REGISTRY_CLEANUP_V1_OK"
