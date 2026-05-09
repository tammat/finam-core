#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.oms.order_journal import OmsOrderJournal
from finam_core.oms.order_state_machine import OrderStatus

journal = OmsOrderJournal()
journal.ensure_schema()

client_order_id = journal.build_client_order_id(
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    strategy="broker_status_update_test",
    ts_bucket=str(time.time_ns()),
)

created, rec = journal.create_if_absent(
    client_order_id=client_order_id,
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    order_type="LIMIT",
    status="CREATED",
    source="broker_status_update_test",
    payload={"test": True},
)

assert created is True, rec

mapping1 = journal.update_status_from_broker_order({
    "client_order_id": client_order_id,
    "order_id": "broker_order_001",
    "status": "PENDING_NEW",
})
assert mapping1.oms_status == OrderStatus.SENT, mapping1

mapping2 = journal.update_status_from_broker_order({
    "clientOrderId": client_order_id,
    "orderId": "broker_order_001",
    "status": "WORKING",
})
assert mapping2.oms_status == OrderStatus.ACCEPTED, mapping2

mapping3 = journal.update_status_from_broker_order({
    "clientId": client_order_id,
    "brokerOrderId": "broker_order_001",
    "orderStatus": "MATCHED",
})
assert mapping3.oms_status == OrderStatus.FILLED, mapping3

try:
    journal.update_status_from_broker_order({
        "client_order_id": client_order_id,
        "order_id": "broker_order_001",
        "status": "CANCELLED",
    })
except RuntimeError as exc:
    assert "invalid_transition:FILLED->CANCELLED" in str(exc), exc
else:
    raise AssertionError("Expected invalid broker status transition was not blocked")

print("OMS_UPDATE_STATUS_FROM_BROKER_ORDER_OK", client_order_id)
PY
