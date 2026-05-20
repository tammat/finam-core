#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_state_supervisor.py

grep -q "TRAILING_EXIT_SHADOW_SELL_ENABLED" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "TRAILING_EXIT_FORCE_TRIGGER" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "execution_mode" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "'shadow'" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "TRAILING_EXIT_SHADOW_SELL_INTENT_CREATED" src/scripts/run_trailing_exit_state_supervisor.py

echo "OK: trailing exit real shadow sell"
