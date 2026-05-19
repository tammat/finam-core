#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/restore_runtime_state.py \
  src/scripts/runtime_supervisor.py

grep -q "RUNTIME_STATE_RESTORE_CHECK" src/scripts/restore_runtime_state.py
grep -q "run_restore_check" src/scripts/runtime_supervisor.py

echo "OK: runtime state restore"
