#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_protective_lifecycle_manager.py

grep -q "PROTECTIVE_STOP_INTENT_CREATED" src/scripts/run_protective_lifecycle_manager.py
grep -q "protective_stop_shadow" src/scripts/run_protective_lifecycle_manager.py
grep -q "PROTECTIVE_REAL_ARMED" src/scripts/run_protective_lifecycle_manager.py
grep -q "order_type','stop" src/scripts/run_protective_lifecycle_manager.py

echo "OK: protective lifecycle manager"
