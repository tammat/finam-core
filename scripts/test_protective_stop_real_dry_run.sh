#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_protective_stop_real_execution_adapter.py

grep -q "PROTECTIVE_REAL_DRY_RUN" src/scripts/run_protective_stop_real_execution_adapter.py
grep -q "PROTECTIVE_REAL_DRY_RUN_WOULD_SEND" src/scripts/run_protective_stop_real_execution_adapter.py
grep -q "protective_real_dry_run" src/scripts/run_protective_stop_real_execution_adapter.py

echo "OK: protective stop real dry run"
