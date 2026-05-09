#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.oms.order_journal import OmsOrderJournal

journal = OmsOrderJournal()
journal.ensure_schema()

client_order_id = journal.build_client_order_id(
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    strategy="fsm_test",
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
    source="fsm_test",
    payload={"fsm_test": True},
)

assert created is True, rec

journal.update_status(
    client_order_id=client_order_id,
    status="SENT",
    broker_order_id="broker_fsm_001",
)

journal.update_status(
    client_order_id=client_order_id,
    status="ACCEPTED",
)

journal.update_status(
    client_order_id=client_order_id,
    status="FILLED",
)

try:
    journal.update_status(
        client_order_id=client_order_id,
        status="CANCELLED",
    )
except RuntimeError as exc:
    assert "invalid_transition:FILLED->CANCELLED" in str(exc), exc
else:
    raise AssertionError("Expected invalid FSM transition was not blocked")

print("OMS_ORDER_JOURNAL_FSM_OK", client_order_id)
PY
