#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime_health_supervisor_v2.py

grep -q "RUNTIME_HEALTH_SUPERVISOR_V2_OK" src/scripts/runtime_health_supervisor_v2.py
grep -q "portfolio_execution_queue" src/scripts/runtime_health_supervisor_v2.py
grep -q "execution_intents" src/scripts/runtime_health_supervisor_v2.py
grep -q "portfolio_reconciliation_events" src/scripts/runtime_health_supervisor_v2.py

echo "OK: runtime health supervisor v2"
