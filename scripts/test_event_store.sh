#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore

store = EventStore()
store.ensure_schema()

aggregate_id = f"test_order_{time.time_ns()}"

payload = {
    "symbol": "NGH6@RTSX",
    "side": "BUY",
    "qty": 1.0,
    "ts": time.time_ns(),
}

created1, event1 = store.append(
    event_type="ORDER_CREATED",
    aggregate_type="order",
    aggregate_id=aggregate_id,
    source="test",
    payload=payload,
)

created2, event2 = store.append(
    event_type="ORDER_CREATED",
    aggregate_type="order",
    aggregate_id=aggregate_id,
    source="test",
    payload=payload,
    event_id=event1.event_id,
)

assert created1 is True, created1
assert created2 is False, created2
assert event1.event_id == event2.event_id

store.append(
    event_type="ORDER_SENT",
    aggregate_type="order",
    aggregate_id=aggregate_id,
    source="test",
    payload={"broker_order_id": "broker_evt_001"},
)

events = store.list_by_aggregate(
    aggregate_type="order",
    aggregate_id=aggregate_id,
)

assert len(events) >= 2, events
assert events[0].event_type == "ORDER_CREATED", events
assert events[1].event_type == "ORDER_SENT", events

print("EVENT_STORE_OK", aggregate_id)
PY
