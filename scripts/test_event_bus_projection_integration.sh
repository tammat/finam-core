#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_projection_bridge import EventProjectionBridge
from finam_core.events.event_store import EventStore
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
subscriber = RealtimeProjectionSubscriber(store=projection_store)

bridge = EventProjectionBridge(
    event_bus=bus,
    subscriber=subscriber,
)
attached = bridge.attach()

assert attached.subscribed is True, attached
assert attached.mode == "typed", attached

store = EventStore(event_bus=bus)

aggregate_id = f"event_bus_projection_{time.time_ns()}"

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

store.append(
    event_type="PIPE_FILLED",
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
    source="test",
    payload={
        "symbol": "NGH6@RTSX",
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
    },
)

order = projection_store.get_order(aggregate_id)
position = projection_store.get_position("NGH6@RTSX")
portfolio = projection_store.get_portfolio()

assert order is not None, order
assert order["status"] == "SENT", order

assert position is not None, position
assert abs(float(position["qty"]) - 1.0) < 0.000001, position

assert portfolio is not None, portfolio
assert abs(float(portfolio["exposure"]) - 100.0) < 0.000001, portfolio

print("EVENT_BUS_PROJECTION_INTEGRATION_OK", aggregate_id)
PY
