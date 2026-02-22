#!/usr/bin/env bash
set -e

echo "=== PYTHONPATH ==="
export PYTHONPATH=$PWD/infra/finam/grpc

echo "=== Import test ==="
python3 - <<'PY'
import grpc.tradeapi.v1.orders.orders_service_pb2 as orders
print("OK: orders_service_pb2 loaded")
print("Services:", orders.DESCRIPTOR.services_by_name.keys())
PY

echo "=== DONE ==="