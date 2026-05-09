#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.oms.order_journal import OmsOrderJournal
from finam_core.reconciliation.active_orders_reconciliation import ActiveOrdersReconciliation


class FakeOrdersClient:
    def __init__(self, orders):
        self._orders = orders

    def get_orders(self):
        return self._orders


class FakeRepository:
    def list_all(self):
        return []


class FakeManagedService:
    def __init__(self):
        self.repository = FakeRepository()


journal = OmsOrderJournal()
journal.ensure_schema()

client_order_id = journal.build_client_order_id(
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    strategy="active_recon_oms_sync",
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
    source="active_recon_oms_sync",
    payload={"test": True},
)

assert created is True, rec

orders = [
    {
        "client_order_id": client_order_id,
        "order_id": "broker_active_001",
        "symbol": "NGH6@RTSX",
        "status": "PENDING_NEW",
    }
]

recon = ActiveOrdersReconciliation(
    orders_client=FakeOrdersClient(orders),
    managed_service=FakeManagedService(),
    oms_journal=journal,
)

issues = recon.check()

assert issues == [], issues

print("ACTIVE_ORDERS_RECONCILIATION_OMS_SYNC_OK", client_order_id)
PY
