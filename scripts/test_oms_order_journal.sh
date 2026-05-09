#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
from finam_core.oms.order_journal import OmsOrderJournal

journal = OmsOrderJournal()
journal.ensure_schema()

client_order_id = journal.build_client_order_id(
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    strategy="test",
    ts_bucket="20260509T1000",
)

created1, rec1 = journal.create_if_absent(
    client_order_id=client_order_id,
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    order_type="LIMIT",
    status="CREATED",
    source="test",
    payload={"test": True},
)

created2, rec2 = journal.create_if_absent(
    client_order_id=client_order_id,
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    order_type="LIMIT",
    status="CREATED",
    source="test",
    payload={"test": True},
)

assert created1 is True
assert created2 is False
assert rec1.client_order_id == rec2.client_order_id

journal.update_status(
    client_order_id=client_order_id,
    status="SENT",
    broker_order_id="broker_test_001",
)

print("OMS_ORDER_JOURNAL_OK", client_order_id)
PY
