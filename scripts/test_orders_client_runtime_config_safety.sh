#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/config/runtime_config.py \
  src/finam_core/adapters/grpc/orders_client.py

grep -q "RuntimeConfig" src/finam_core/adapters/grpc/orders_client.py
grep -q 'runtime_config.get("FINAM_TOKEN"' src/finam_core/adapters/grpc/orders_client.py
grep -q 'runtime_config.get("FINAM_ACCOUNT_ID"' src/finam_core/adapters/grpc/orders_client.py
grep -q 'runtime_config.get("FINAM_GRPC_ENDPOINT"' src/finam_core/adapters/grpc/orders_client.py
grep -q 'runtime_config.get_bool("REAL_EXECUTION_ENABLED"' src/finam_core/adapters/grpc/orders_client.py
grep -q 'runtime_config.get_bool("REAL_ORDER_CONFIRM"' src/finam_core/adapters/grpc/orders_client.py

if grep -q 'os.getenv("REAL_EXECUTION_ENABLED"' src/finam_core/adapters/grpc/orders_client.py; then
    echo "DIRECT_REAL_EXECUTION_ENABLED_GETENV_STILL_PRESENT"
    exit 1
fi

if grep -q 'os.getenv("REAL_ORDER_CONFIRM"' src/finam_core/adapters/grpc/orders_client.py; then
    echo "DIRECT_REAL_ORDER_CONFIRM_GETENV_STILL_PRESENT"
    exit 1
fi

echo "ORDERS_CLIENT_RUNTIME_CONFIG_SAFETY_OK"
