#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_order_acks.sql
test -f src/finam_core/execution/order_ack_logger.py

grep -q "CREATE TABLE IF NOT EXISTS order_acks" sql/20260511_order_acks.sql
grep -q "idx_order_acks_order_id" sql/20260511_order_acks.sql
grep -q "class OrderAckLogger" src/finam_core/execution/order_ack_logger.py
grep -q "ORDER_ACK_LOG_FAILED" src/finam_core/execution/order_ack_logger.py
grep -q "OrderAckLogger" src/finam_core/adapters/grpc/orders_client.py
grep -q 'self.order_ack_logger.log(ack, source="market_order")' src/finam_core/adapters/grpc/orders_client.py
grep -q 'self.order_ack_logger.log(ack, source="stop_order")' src/finam_core/adapters/grpc/orders_client.py
grep -q 'self.order_ack_logger.log(ack, source="limit_order")' src/finam_core/adapters/grpc/orders_client.py

python -m py_compile src/finam_core/execution/order_ack.py
python -m py_compile src/finam_core/execution/order_ack_logger.py
python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "ORDER_ACK_LOGGER_TEST_OK"
