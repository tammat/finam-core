#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_state_supervisor.py

grep -q "trailing_exit_state" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "highest_price_since_entry" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "trailing_stop_price" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "TRAILING_EXIT_INTENT_CREATED" src/scripts/run_trailing_exit_state_supervisor.py

echo "OK: trailing exit state supervisor"
