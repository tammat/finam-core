#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_trailing_exit_dry_run_audit.py

grep -q "TRAILING_DRY_RUN_AUDIT" src/scripts/run_trailing_exit_dry_run_audit.py
grep -q "exit_required" src/scripts/run_trailing_exit_dry_run_audit.py
grep -q "new_high" src/scripts/run_trailing_exit_dry_run_audit.py
grep -q "new_stop" src/scripts/run_trailing_exit_dry_run_audit.py

echo "OK: trailing exit dry run audit"
