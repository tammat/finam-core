#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/adapters/grpc/orders_client.py \
  src/scripts/run_protective_stop_real_execution_adapter.py

grep -q "client_order_id: str | None = None" \
  src/finam_core/adapters/grpc/orders_client.py

grep -q "client_order_id=client_order_id" \
  src/finam_core/adapters/grpc/orders_client.py

grep -q "client_order_id=client_order_id" \
  src/scripts/run_protective_stop_real_execution_adapter.py

echo "OK: protective stop client_order_id wiring"
