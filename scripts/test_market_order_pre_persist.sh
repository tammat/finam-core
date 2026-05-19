#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_real_buy_execution_adapter.py \
  src/finam_core/execution/execution_lifecycle_determinism.py

grep -q "REAL_BUY_MARKET_PRE_PERSIST" src/scripts/run_real_buy_execution_adapter.py
grep -q "real_buy_market_pre_persist_before_broker_call" src/scripts/run_real_buy_execution_adapter.py
grep -q '"SENDING"' src/finam_core/execution/execution_lifecycle_determinism.py

echo "OK: market order pre persist"
