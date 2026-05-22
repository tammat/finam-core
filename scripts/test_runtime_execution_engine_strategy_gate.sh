#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_execution_engine.py \
  src/finam_core/runtime/runtime_strategy_selection_provider.py

grep -q "RUNTIME_STRATEGY_SELECTION_BLOCK" src/finam_core/runtime/runtime_execution_engine.py
grep -q "strategy_selection_provider.allow_worker" src/finam_core/runtime/runtime_execution_engine.py

echo "TEST_RUNTIME_EXECUTION_ENGINE_STRATEGY_GATE_OK"
