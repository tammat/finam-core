#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_runtime_loop.py

grep -q "TRAILING_EXIT_LOOP_TICK" src/scripts/run_trailing_exit_runtime_loop.py
grep -q "TRAILING_EXIT_RUNTIME_LOOP_OK" src/scripts/run_trailing_exit_runtime_loop.py
grep -q "TRAILING_EXIT_LOOP_INTERVAL_SEC" src/scripts/run_trailing_exit_runtime_loop.py

echo "OK: trailing exit runtime loop"
