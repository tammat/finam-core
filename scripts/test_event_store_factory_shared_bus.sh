#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_projection_bridge import EventProjectionBridge
from finam_core.events.event_store_factory import EventStoreFactory
from finam_core.projections.projection_store import ProjectionStore
from finam_core.projections.realtime_projection_subscriber import RealtimeProjectionSubscriber


class FakeEventBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, event_type, handler):
        self.handlers.setdefault(event_type, []).append(handler)

    def publish(self, event_type, event):
        for handler in self.handlers.get(event_type, []):
            handler(event_type, event)


bus = FakeEventBus()
projection_store = ProjectionStore()

bridge = EventProjectionBridge(
    event_bus=bus,
    subscriber=RealtimeProjectionSubscriber(store=projection_store),
)
bridge.attach()

EventStoreFactory.configure(event_bus=bus)

store = EventStoreFactory.create()

aggregate_id = f"event_store_factory_{time.time_ns()}"

created, event = store.append(
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

assert created is True, event

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

order = projection_store.get_order(aggregate_id)

assert order is not None, order
assert order["status"] == "SENT", order

print("EVENT_STORE_FACTORY_SHARED_BUS_OK", aggregate_id)
PY
