#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.events.event_store_reader import EventStoreReader

store = EventStore()
reader = EventStoreReader()

aggregate_id = f"reader_test_{time.time_ns()}"

store.append(
    event_type="ORDER_CREATED",
    aggregate_type="order",
    aggregate_id=aggregate_id,
    source="reader_test",
    payload={
        "symbol": "NGH6@RTSX",
        "side": "BUY",
    },
)

store.append(
    event_type="ORDER_SENT",
    aggregate_type="order",
    aggregate_id=aggregate_id,
    source="reader_test",
    payload={
        "broker_order_id": "broker_reader_001",
    },
)

# list_by_type
events_created = reader.list_by_type(
    event_type="ORDER_CREATED",
    limit=10,
)

assert any(x.aggregate_id == aggregate_id for x in events_created), events_created

# replay aggregate
replay = reader.replay_aggregate(
    aggregate_type="order",
    aggregate_id=aggregate_id,
)

assert len(replay.events) >= 2, replay
assert replay.events[0].event_type == "ORDER_CREATED", replay.events
assert replay.events[1].event_type == "ORDER_SENT", replay.events

# iterator
all_events = list(reader.iter_all(batch_size=10))
assert len(all_events) > 0, all_events

print("EVENT_STORE_READER_OK", aggregate_id)
PY
