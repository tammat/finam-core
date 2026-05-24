#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py

grep -q "runtime_strategy_selection" src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py
grep -q "runtime_strategy_scores" src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py
grep -q "RUNTIME_STRATEGY_SCORES_SYNC_OK" src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py

echo "RUNTIME_STRATEGY_SCORES_SYNC_TEST_OK"
