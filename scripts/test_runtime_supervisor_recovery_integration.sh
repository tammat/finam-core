#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_supervisor.py \
  src/scripts/run_runtime_recovery_coordinator_v2.py

grep -q "run_recovery_coordinator" src/scripts/runtime_supervisor.py
grep -q "run_runtime_recovery_coordinator_v2.py" src/scripts/runtime_supervisor.py

echo "OK: runtime supervisor recovery integration"
