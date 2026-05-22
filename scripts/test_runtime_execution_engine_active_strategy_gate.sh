#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_active_strategy_provider.py \
  src/finam_core/runtime/runtime_strategy_selection_provider.py \
  src/finam_core/runtime/runtime_execution_engine.py

grep -q "RuntimeActiveStrategyProvider" src/finam_core/runtime/runtime_execution_engine.py
grep -q "NO_ACTIVE_STRATEGY" src/finam_core/runtime/runtime_execution_engine.py
! grep -q "_resolve_runtime_strategy" src/finam_core/runtime/runtime_execution_engine.py
! grep -q "_resolve_runtime_timeframe" src/finam_core/runtime/runtime_execution_engine.py

echo "TEST_RUNTIME_EXECUTION_ENGINE_ACTIVE_STRATEGY_GATE_OK"
