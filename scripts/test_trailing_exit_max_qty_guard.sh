#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_state_supervisor.py

grep -q "TRAILING_EXIT_MAX_QTY" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "TRAILING_EXIT_STALE_POSITION_BLOCKED" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "exit_qty = min(qty, max_qty)" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "raw_qty" src/scripts/run_trailing_exit_state_supervisor.py

echo "OK: trailing exit max qty guard"
