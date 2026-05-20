#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/adapters/grpc/orders_client.py

grep -q "REAL_ORDER_VALID_BEFORE" src/finam_core/adapters/grpc/orders_client.py
grep -q "_valid_before_from_env" src/finam_core/adapters/grpc/orders_client.py
grep -q "VALID_BEFORE_GOOD_TILL_CANCEL" src/finam_core/adapters/grpc/orders_client.py

echo "OK: order validity policy"
