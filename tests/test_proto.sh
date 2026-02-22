#!/bin/bash
export PYTHONPATH=$PWD

python3 - <<EOF
from infra.finam.proto.grpc.tradeapi.v1.orders import orders_service_pb2
from infra.finam.proto.grpc.tradeapi.v1.auth import auth_service_pb2
print("PROTO OK")
EOF