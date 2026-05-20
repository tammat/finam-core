#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/adapters/grpc/orders_client.py \
  src/finam_core/execution/finam_order_client_adapter.py \
  src/scripts/run_real_buy_execution_adapter.py \
  src/scripts/run_real_sell_execution_adapter.py

grep -q "def place_buy_limit" src/finam_core/execution/finam_order_client_adapter.py
grep -q "def place_buy_market" src/finam_core/execution/finam_order_client_adapter.py
grep -q "def place_sell_limit" src/finam_core/execution/finam_order_client_adapter.py
grep -q "def place_sell_market" src/finam_core/execution/finam_order_client_adapter.py
grep -q "REAL_SELL_MARKET_ENABLED" src/scripts/run_real_sell_execution_adapter.py
grep -q "client_order_id=client_order_id" src/scripts/run_real_buy_execution_adapter.py
grep -q "client_order_id=client_order_id" src/scripts/run_real_sell_execution_adapter.py

echo "OK: all order types pass client_order_id"
