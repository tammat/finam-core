#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_real_buy_execution_adapter.py

grep -q "REAL_MARKET_ORDER_TIMEOUT_SEC" src/scripts/run_real_buy_execution_adapter.py
grep -q "real_buy_market_order_timeout" src/scripts/run_real_buy_execution_adapter.py
grep -q "signal.alarm" src/scripts/run_real_buy_execution_adapter.py

echo "OK: real market order timeout guard"
