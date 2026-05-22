#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/sync_runtime_active_universe_from_strategy_selection.py \
  src/finam_core/runtime/runtime_active_strategy_provider.py

grep -q "runtime_strategy_selection" src/scripts/sync_runtime_active_universe_from_strategy_selection.py
grep -q "runtime_active_universe" src/scripts/sync_runtime_active_universe_from_strategy_selection.py

echo "TEST_SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_STRATEGY_SELECTION_OK"
