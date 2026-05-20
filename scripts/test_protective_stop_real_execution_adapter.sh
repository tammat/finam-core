#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_protective_stop_real_execution_adapter.py

grep -q "REAL_SELL_STOP_ENABLED" \
  src/scripts/run_protective_stop_real_execution_adapter.py

grep -q "PROTECTIVE_REAL_SENT" \
  src/scripts/run_protective_stop_real_execution_adapter.py

grep -q "place_stop_order" \
  src/scripts/run_protective_stop_real_execution_adapter.py

grep -q "client_order_id" \
  src/scripts/run_protective_stop_real_execution_adapter.py

echo "OK: protective stop real execution adapter"
