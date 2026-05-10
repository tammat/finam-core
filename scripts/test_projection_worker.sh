#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.projections.projection_store import ProjectionStore
from finam_core.projections.projection_worker import ProjectionWorker

store = EventStore()
projection_store = ProjectionStore()

checkpoint_name = f"projection_worker_test_{time.time_ns()}"
aggregate_id = f"projection_worker_order_{time.time_ns()}"

store.append(
    event_type="ORDER_CREATED",
    aggregate_type="order",
    aggregate_id=aggregate_id,
    source="test",
    payload={
        "client_order_id": aggregate_id,
        "symbol": "NGH6@RTSX",
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
    },
)

store.append(
    event_type="OMS_ORDER_STATUS_UPDATED",
    aggregate_type="order",
    aggregate_id=aggregate_id,
    source="test",
    payload={
        "client_order_id": aggregate_id,
        "old_status": "CREATED",
        "new_status": "SENT",
    },
)

worker = ProjectionWorker(
    checkpoint_name=checkpoint_name,
    interval_sec=0.1,
    limit=10000,
)

r1 = worker.tick()

assert r1.ok is True, r1
assert r1.events_loaded > 0, r1
assert r1.new_event_id > r1.previous_event_id, r1

order = projection_store.get_order(aggregate_id)

assert order is not None, order
assert order["status"] == "SENT", order

r2 = worker.tick()

assert r2.ok is True, r2
assert r2.events_loaded == 0, r2
assert r2.previous_event_id == r1.new_event_id, (r1, r2)
assert r2.new_event_id == r1.new_event_id, (r1, r2)

print("PROJECTION_WORKER_OK", checkpoint_name)
PY
