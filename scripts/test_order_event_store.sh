#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
export PYTHONPATH=src

python - <<'PY'
import uuid
from finam_core.storage.postgres_order_event_store import PostgresOrderEventStore

store = PostgresOrderEventStore()
oid = f"test_{uuid.uuid4().hex[:8]}"

store.log_event(
    order_id=oid,
    symbol="BRM6@RTSX",
    side="BUY",
    state="ACCEPTED",
    qty=3,
    filled_qty=1,
    remaining_qty=2,
    fill_price=100.5,
    avg_fill_price=100.5,
    raw_json={"source": "test"},
)

print("ORDER_EVENT_STORE_OK")
print(oid)
PY
