#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_strategy_selection_provider.py

grep -q "PAPER_ENABLED" src/finam_core/runtime/runtime_strategy_selection_provider.py
grep -q "allow_worker" src/finam_core/runtime/runtime_strategy_selection_provider.py

echo "TEST_RUNTIME_STRATEGY_SELECTION_PROVIDER_OK"
