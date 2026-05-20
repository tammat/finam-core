#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/adapters/grpc/orders_client.py \
  src/finam_core/execution/finam_order_client_adapter.py \
  src/scripts/run_real_buy_execution_adapter.py \
  src/scripts/run_real_sell_execution_adapter.py

grep -q "client_order_id: str | None = None" src/finam_core/adapters/grpc/orders_client.py
grep -q "client_order_id=client_order_id or self._make_client_order_id()" src/finam_core/adapters/grpc/orders_client.py
grep -q "client_order_id=client_order_id" src/finam_core/execution/finam_order_client_adapter.py
grep -q "client_order_id=client_order_id" src/scripts/run_real_buy_execution_adapter.py
grep -q "client_order_id=client_order_id" src/scripts/run_real_sell_execution_adapter.py

echo "OK: pass client order id to Finam"
