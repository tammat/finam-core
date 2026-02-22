#!/usr/bin/env bash
set -e

export PYTHONPATH=$PWD/infra/finam/grpc

echo "=== PYTHONPATH ==="
echo $PYTHONPATH

echo "=== GRPC SMOKE TEST ==="

python3 - <<'EOF'
import os
import grpc

from grpc.tradeapi.v1.accounts import accounts_service_pb2
from grpc.tradeapi.v1.accounts import accounts_service_pb2_grpc

# === CONFIG ===
HOST = "api.finam.ru:443"     # TEST если используешь тестовый JWT
JWT  = os.getenv("FINAM_JWT") # экспортируй перед запуском

if not JWT:
    raise RuntimeError("FINAM_JWT not set")

# === Channel ===
channel = grpc.secure_channel(HOST, grpc.ssl_channel_credentials())

stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

metadata = [
    ("authorization", f"Bearer {JWT}")
]

print("Connecting...")

try:
    response = stub.GetAccounts(
        accounts_service_pb2.AccountsRequest(),
        metadata=metadata,
        timeout=10
    )
    print("OK: Accounts received")
    print("Accounts:", [a.account_id for a in response.accounts])
except Exception as e:
    print("ERROR:", e)
    raise

print("=== DONE ===")
EOF