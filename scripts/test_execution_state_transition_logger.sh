#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/execution_state_transition_logger.py

grep -q "execution_state_transitions" \
  src/finam_core/execution/execution_state_transition_logger.py

grep -q "previous_state" \
  src/finam_core/execution/execution_state_transition_logger.py

grep -q "next_state" \
  src/finam_core/execution/execution_state_transition_logger.py

echo "OK: execution state transition logger"
