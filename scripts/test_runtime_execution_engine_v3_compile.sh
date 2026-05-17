#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_state.py \
  src/finam_core/runtime/runtime_telemetry.py

echo "OK: RuntimeExecutionEngine v3 telemetry/state compile"
