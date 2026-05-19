#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_real_buy_execution_adapter.py

grep -q "RECONCILE_REQUIRED" src/scripts/run_real_buy_execution_adapter.py
grep -q "REAL_BUY_MARKET_TIMEOUT_RECONCILE_REQUIRED" src/scripts/run_real_buy_execution_adapter.py
grep -q "real_buy_market_timeout_reconcile_required" src/scripts/run_real_buy_execution_adapter.py

echo "OK: market order pending reconcile"
