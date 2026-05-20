#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_state_supervisor.py

grep -q "TRAILING_EXIT_LIVE_DRY_RUN" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "TRAILING_EXIT_LIVE_DRY_RUN_WOULD_CREATE_SELL" src/scripts/run_trailing_exit_state_supervisor.py
grep -q "live_dry_run=1" src/scripts/run_trailing_exit_state_supervisor.py

echo "OK: trailing exit state live dry run"
