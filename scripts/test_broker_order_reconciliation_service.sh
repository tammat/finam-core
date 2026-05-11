#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/finam_core/reconciliation/broker_order_reconciliation.py

PYTHONPATH=src python - <<'PY'
from finam_core.execution.order_ack import OrderAck
from finam_core.reconciliation.broker_order_reconciliation import (
    BrokerOrderReconciliationService,
    BrokerOrderState,
)

ack_ok = OrderAck(True, "SBER@MISX", "BUY", 1, "ord_1", "PLACED")
ack_missing = OrderAck(True, "SBER@MISX", "BUY", 1, "ord_404", "PLACED")
ack_no_id = OrderAck(True, "SBER@MISX", "BUY", 1, None, "PLACED")

service = BrokerOrderReconciliationService([
    BrokerOrderState(order_id="ord_1", symbol="SBER@MISX", side="BUY", status="ORDER_STATUS_NEW")
])

assert service.check_ack(ack_ok) == []
assert service.check_ack(ack_missing)[0].issue_type == "ACK_MISSING_AT_BROKER"
assert service.check_ack(ack_no_id)[0].issue_type == "ACK_WITHOUT_ORDER_ID"

print("BROKER_ORDER_RECONCILIATION_RUNTIME_OK")
PY

python -m py_compile src/finam_core/reconciliation/broker_order_reconciliation.py

echo "BROKER_ORDER_RECONCILIATION_SERVICE_TEST_OK"
