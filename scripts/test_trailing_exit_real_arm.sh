#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_state_supervisor.py

grep -q "TRAILING_EXIT_REAL_ARMED" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "TRAILING_EXIT_REAL_NOT_ARMED_WOULD_CREATE_SELL" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "real_armed=0" src/scripts/run_trailing_exit_state_supervisor.py

echo "OK: trailing exit real arm"
