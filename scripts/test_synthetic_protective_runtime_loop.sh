#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_runtime_loop.py

grep -q "run_real_portfolio_position_sync.py" src/scripts/run_trailing_exit_runtime_loop.py
grep -q "run_real_portfolio_price_sync.py" src/scripts/run_trailing_exit_runtime_loop.py
grep -q "run_synthetic_protective_trigger.py" src/scripts/run_trailing_exit_runtime_loop.py
grep -q "run_trailing_exit_state_supervisor.py" src/scripts/run_trailing_exit_runtime_loop.py

echo "OK: synthetic protective runtime loop"
