#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "def get_orders" src/finam_core/adapters/grpc/orders_client.py
grep -q "GetOrders" src/finam_core/adapters/grpc/orders_client.py

test -f src/finam_core/reconciliation/order_ack_repository.py
test -f src/scripts/reconcile_order_acks.py

grep -q "class OrderAckRepository" src/finam_core/reconciliation/order_ack_repository.py
grep -q "BrokerOrderReconciliationService" src/scripts/reconcile_order_acks.py
grep -q "ORDER_ACK_RECONCILIATION" src/scripts/reconcile_order_acks.py
grep -q "ORDER_ACK_RECON_ISSUE" src/scripts/reconcile_order_acks.py

python -m py_compile src/finam_core/adapters/grpc/orders_client.py
python -m py_compile src/finam_core/reconciliation/order_ack_repository.py
python -m py_compile src/scripts/reconcile_order_acks.py

echo "ORDER_ACK_BROKER_SOURCE_TEST_OK"
