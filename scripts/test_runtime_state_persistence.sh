#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/save_runtime_state_snapshot.py \
  src/scripts/check_runtime_state_restore.py

echo "OK: runtime state persistence compile"
