#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.projections.projection_store import ProjectionStore
from finam_core.projections.projection_updater import ProjectionUpdater

store = EventStore()
projection_store = ProjectionStore()
updater = ProjectionUpdater(store=projection_store)

aggregate_id = f"projection_updater_{time.time_ns()}"

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

result = updater.update_all(batch_size=1000)

assert result.events_loaded > 0, result
assert result.events_processed > 0, result
assert result.orders_count > 0, result
assert result.positions_count > 0, result

order = projection_store.get_order(aggregate_id)
position = projection_store.get_position("NGH6@RTSX")
portfolio = projection_store.get_portfolio()

assert order is not None, order
assert order["status"] == "SENT", order
assert position is not None, position
assert portfolio is not None, portfolio

print("PROJECTION_UPDATER_OK", aggregate_id)
PY
