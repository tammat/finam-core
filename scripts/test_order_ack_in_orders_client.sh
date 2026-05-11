#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/finam_core/adapters/grpc/orders_client.py"

grep -q "from finam_core.execution.order_ack import OrderAck" "$FILE"
grep -q "def _build_order_ack" "$FILE"
grep -q "PLACE_ORDER_NO_ACK" "$FILE"
grep -q 'raw={"ack": ack.__dict__}' "$FILE"
grep -q '"raw": {"ack": ack.__dict__}' "$FILE"

! grep -q 'raw={"response": str(response)}' "$FILE"

python -m py_compile src/finam_core/execution/order_ack.py
python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "ORDER_ACK_IN_ORDERS_CLIENT_TEST_OK"
