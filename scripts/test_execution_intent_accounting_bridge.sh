#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_execution_intent_accounting_bridge.py

grep -q "EXECUTION_INTENT_ACCOUNTING_BRIDGE_OK" \
  src/scripts/run_execution_intent_accounting_bridge.py

grep -q "real_portfolio_positions" \
  src/scripts/run_execution_intent_accounting_bridge.py

echo "OK: execution intent accounting bridge"
