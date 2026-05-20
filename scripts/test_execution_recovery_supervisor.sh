#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_execution_recovery_supervisor.py

grep -q "EXECUTION_RECOVERY_STEP_BEGIN" \
  src/scripts/run_execution_recovery_supervisor.py

grep -q "EXECUTION_STALE_WATCHDOG_OK" \
  src/scripts/run_execution_recovery_supervisor.py

grep -q "OMS_HEALTH_STATE" \
  src/scripts/run_execution_recovery_supervisor.py

grep -q "OMS_HEALTH_UNRESOLVED" \
  src/scripts/run_execution_recovery_supervisor.py

grep -q "EXECUTION_RECOVERY_SUPERVISOR_OK" \
  src/scripts/run_execution_recovery_supervisor.py

echo "OK: execution recovery supervisor"
