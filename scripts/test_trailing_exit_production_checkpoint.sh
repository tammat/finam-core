#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_production_checkpoint.py

grep -q "run_trailing_exit_dry_run_audit.py" src/scripts/run_trailing_exit_production_checkpoint.py
grep -q "run_trailing_exit_runtime_loop.py" src/scripts/run_trailing_exit_production_checkpoint.py
grep -q "TRAILING_EXIT_PRODUCTION_CHECKPOINT_OK" src/scripts/run_trailing_exit_production_checkpoint.py

echo "OK: trailing exit production checkpoint"
