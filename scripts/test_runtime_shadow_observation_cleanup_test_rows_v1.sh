#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_SHADOW_OBSERVATION_CLEANUP_TEST_ROWS_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_shadow_observation_cleanup_test_rows_v1.py

python src/scripts/analytics/build_runtime_shadow_observation_cleanup_test_rows_v1.py

echo "TEST_RUNTIME_SHADOW_OBSERVATION_CLEANUP_TEST_ROWS_V1_OK"
