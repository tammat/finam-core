#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

REPO="src/finam_core/execution/protective_order_link_repository.py"
CLIENT="src/finam_core/adapters/grpc/orders_client.py"

grep -q "def attach_protective_order" "$REPO"
grep -q "PROTECTIVE_ORDER_LINK_ATTACH_FAILED" "$REPO"
grep -q "attached_protective_type" "$REPO"
grep -q 'protective_type="stop"' "$CLIENT"
grep -q 'protective_type="take"' "$CLIENT"
grep -q 'self.order_ack_logger.log(ack, source="stop_order")' "$CLIENT"
grep -q 'self.order_ack_logger.log(ack, source="limit_order")' "$CLIENT"

PYTHONPATH=src python - <<'PY'
from pathlib import Path

client = Path("src/finam_core/adapters/grpc/orders_client.py").read_text(encoding="utf-8")

stop_log = client.index('self.order_ack_logger.log(ack, source="stop_order")')
stop_attach = client.index('protective_type="stop"', stop_log)

limit_log = client.index('self.order_ack_logger.log(ack, source="limit_order")')
limit_attach = client.index('protective_type="take"', limit_log)

assert stop_attach > stop_log
assert limit_attach > limit_log

print("PROTECTIVE_ORDER_LINK_ATTACH_AFTER_STOP_TAKE_ACK_RUNTIME_OK")
PY

python -m py_compile src/finam_core/execution/protective_order_link_repository.py
python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "PROTECTIVE_ORDER_LINK_ATTACH_AFTER_STOP_TAKE_ACK_TEST_OK"
