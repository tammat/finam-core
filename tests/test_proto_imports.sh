#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT"

python3 - <<'PY'
import grpc
print("grpc from:", grpc.__file__)
print("has __version__:", hasattr(grpc, "__version__"))

from infra.finam.finam_grpc_api.grpc.tradeapi.v1.orders import orders_service_pb2, orders_service_pb2_grpc
from infra.finam.finam_grpc_api.grpc.tradeapi.v1.auth import auth_service_pb2, auth_service_pb2_grpc
from infra.finam.finam_grpc_api.grpc.tradeapi.v1.accounts import accounts_service_pb2, accounts_service_pb2_grpc

print("PROTO IMPORT OK")
print("OrdersService:", hasattr(orders_service_pb2_grpc, "OrdersServiceStub"))
print("AuthService:", hasattr(auth_service_pb2_grpc, "AuthServiceStub"))
print("AccountsService:", hasattr(accounts_service_pb2_grpc, "AccountsServiceStub"))
PY
