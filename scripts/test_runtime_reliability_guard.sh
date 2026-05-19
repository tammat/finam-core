#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_reliability_guard.py \
  src/scripts/run_real_buy_execution_adapter.py

grep -q "RUNTIME_RELIABILITY_GUARD_CRITICAL" src/scripts/runtime_reliability_guard.py
grep -q "runtime_risk_freeze" src/scripts/runtime_reliability_guard.py
grep -q "runtime_risk_freeze" src/scripts/run_real_buy_execution_adapter.py

echo "OK: runtime reliability guard"
