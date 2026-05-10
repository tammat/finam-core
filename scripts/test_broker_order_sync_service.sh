#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.oms.order_journal import OmsOrderJournal
from finam_core.reconciliation.broker_order_sync_service import BrokerOrderSyncService


class FakeOrdersClient:
    def __init__(self, orders):
        self._orders = orders

    def get_orders(self):
        return self._orders


journal = OmsOrderJournal()
journal.ensure_schema()

client_order_id = journal.build_client_order_id(
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    strategy="broker_order_sync_test",
    ts_bucket=str(time.time_ns()),
)

created, _ = journal.create_if_absent(
    client_order_id=client_order_id,
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    order_type="LIMIT",
    status="CREATED",
    source="broker_order_sync_test",
    payload={"test": True},
)

assert created is True

orders = [
    {
        "client_order_id": client_order_id,
        "order_id": "broker_sync_001",
        "symbol": "NGH6@RTSX",
        "status": "PENDING_NEW",
    },
    {
        "order_id": "broker_sync_missing_client",
        "symbol": "BRM6@RTSX",
        "status": "WORKING",
    },
]

service = BrokerOrderSyncService(
    orders_client=FakeOrdersClient(orders),
    oms_journal=journal,
)

result = service.sync_once()

assert result.synced == 1, result
assert result.failed == 1, result
assert result.issues[0].kind == "missing_client_order_id", result.issues

print("BROKER_ORDER_SYNC_SERVICE_OK", client_order_id)
PY
