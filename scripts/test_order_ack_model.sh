#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/finam_core/execution/order_ack.py

grep -q "class OrderAck" src/finam_core/execution/order_ack.py
grep -q "accepted: bool" src/finam_core/execution/order_ack.py
grep -q "order_id: str | None" src/finam_core/execution/order_ack.py

python -m py_compile src/finam_core/execution/order_ack.py

echo "ORDER_ACK_MODEL_TEST_OK"
