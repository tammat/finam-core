#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_runtime_loop.py

grep -q "run_real_portfolio_position_sync.py" src/scripts/run_trailing_exit_runtime_loop.py
grep -q "run_real_portfolio_price_sync.py" src/scripts/run_trailing_exit_runtime_loop.py
grep -q "TRAILING_EXIT_LOOP_STEP_BEGIN" src/scripts/run_trailing_exit_runtime_loop.py

echo "OK: trailing runtime pre sync"
