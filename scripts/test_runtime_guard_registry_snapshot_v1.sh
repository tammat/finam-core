#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "TEST_RUNTIME_GUARD_REGISTRY_SNAPSHOT_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_guard_registry_snapshot_v1.py

python src/scripts/analytics/build_runtime_guard_registry_snapshot_v1.py | tee /tmp/runtime_guard_registry_snapshot_v1.log

grep -q "RUNTIME_GUARD_REGISTRY_SNAPSHOT_V1" /tmp/runtime_guard_registry_snapshot_v1.log
grep -q "RUNTIME_GUARD_REGISTRY_SNAPSHOT_V1_OK" /tmp/runtime_guard_registry_snapshot_v1.log

echo "TEST_RUNTIME_GUARD_REGISTRY_SNAPSHOT_V1_OK"
