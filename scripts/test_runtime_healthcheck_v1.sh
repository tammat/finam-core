#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime/build_runtime_healthcheck_v1.py

python src/scripts/runtime/build_runtime_healthcheck_v1.py --since "30 minutes ago" | grep -q "FINAM_CORE_RUNTIME_HEALTHCHECK_V1_OK"

echo "RUNTIME_HEALTHCHECK_V1_TEST_OK"
