#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime/apply_regime_matrix_runtime_modifier.py

if grep -q 'runtime_action or "UNKNOWN"' \
  src/scripts/runtime/apply_regime_matrix_runtime_modifier.py
then
    echo "UNKNOWN_FALLBACK_STILL_PRESENT"
    exit 1
fi

grep -q "if not runtime_action:" \
  src/scripts/runtime/apply_regime_matrix_runtime_modifier.py

echo "REGIME_UNKNOWN_CLEANUP_OK"
