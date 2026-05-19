#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_operational_dashboard.py

grep -q "RUNTIME_OPERATIONAL_DASHBOARD_OK" \
  src/scripts/runtime_operational_dashboard.py

grep -q "Market anomalies" \
  src/scripts/runtime_operational_dashboard.py

grep -q "runtime-operational-dashboard.timer" \
  scripts/install_runtime_operational_dashboard_timer.sh

echo "OK: runtime operational dashboard"
