#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.projections.checkpoint_aware_projection_updater import CheckpointAwareProjectionUpdater
from finam_core.projections.projection_checkpoint_service import ProjectionCheckpointService
from finam_core.projections.projection_store import ProjectionStore

store = EventStore()
projection_store = ProjectionStore()
checkpoints = ProjectionCheckpointService()
updater = CheckpointAwareProjectionUpdater(
    store=projection_store,
    checkpoints=checkpoints,
)

checkpoint_name = f"checkpoint_aware_{time.time_ns()}"
aggregate_id = f"checkpoint_projection_{time.time_ns()}"

initial = checkpoints.get(name=checkpoint_name)
assert initial.last_event_id == 0, initial

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

r1 = updater.update_since_checkpoint(
    checkpoint_name=checkpoint_name,
    limit=10000,
)

assert r1.events_loaded > 0, r1
assert r1.new_event_id > r1.previous_event_id, r1

order = projection_store.get_order(aggregate_id)
assert order is not None, order
assert order["status"] == "SENT", order

r2 = updater.update_since_checkpoint(
    checkpoint_name=checkpoint_name,
    limit=10000,
)

assert r2.previous_event_id == r1.new_event_id, (r1, r2)
assert r2.events_loaded == 0, r2
assert r2.new_event_id == r1.new_event_id, r2

print("CHECKPOINT_AWARE_PROJECTION_UPDATER_OK", checkpoint_name)
PY
