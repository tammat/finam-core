#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_execution_intent_fill_simulator.py \
  src/finam_core/execution/execution_intent_router.py

grep -q "EXECUTION_INTENT_FILL_SIMULATOR_OK" src/scripts/run_execution_intent_fill_simulator.py
grep -q "portfolio_execution_queue" src/scripts/run_execution_intent_fill_simulator.py
grep -q "paper_fill_simulated" src/scripts/run_execution_intent_fill_simulator.py

echo "OK: execution intent fill simulator"
