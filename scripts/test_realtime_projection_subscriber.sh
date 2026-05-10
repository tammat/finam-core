#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.events.event_store_reader import EventStoreReader
from finam_core.projections.projection_store import ProjectionStore
from finam_core.projections.realtime_projection_subscriber import (
    RealtimeProjectionSubscriber,
)

store = EventStore()
reader = EventStoreReader()
projection_store = ProjectionStore()

subscriber = RealtimeProjectionSubscriber(
    store=projection_store,
)

aggregate_id = f"rt_projection_{time.time_ns()}"

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

events = []
events.extend(
    reader.replay_aggregate(
        aggregate_type="order",
        aggregate_id=aggregate_id,
    ).events
)

events.extend(
    reader.replay_aggregate(
        aggregate_type="portfolio",
        aggregate_id=aggregate_id,
    ).events
)

result = subscriber.process_events(events)

assert result.events_processed >= 3, result
assert result.orders_count >= 1, result
assert result.positions_count >= 1, result

order = projection_store.get_order(aggregate_id)
position = projection_store.get_position("NGH6@RTSX")
portfolio = projection_store.get_portfolio()

assert order is not None, order
assert order["status"] == "SENT", order

assert position is not None, position
assert abs(float(position["qty"]) - 1.0) < 0.000001, position

assert portfolio is not None, portfolio
assert abs(float(portfolio["exposure"]) - 100.0) < 0.000001, portfolio

print("REALTIME_PROJECTION_SUBSCRIBER_OK", aggregate_id)
PY
