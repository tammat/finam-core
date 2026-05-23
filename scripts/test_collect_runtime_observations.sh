#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/collect_runtime_observations.py

grep -q "runtime_observations" src/scripts/collect_runtime_observations.py
grep -q "RUNTIME_OBSERVATIONS_COLLECTED" src/scripts/collect_runtime_observations.py

echo "TEST_COLLECT_RUNTIME_OBSERVATIONS_OK"
