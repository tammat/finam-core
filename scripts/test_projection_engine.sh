#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.events.event_store_reader import EventStoreReader
from finam_core.projections.projection_engine import ProjectionEngine

store = EventStore()
reader = EventStoreReader()
engine = ProjectionEngine()

aggregate_id = f"projection_test_{time.time_ns()}"

created, e1 = store.append(
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

store.append(
    event_type="PIPE_FILLED",
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
    source="test",
    payload={
        "symbol": "NGH6@RTSX",
        "side": "SELL",
        "qty": 1.0,
        "price": 110.0,
    },
)

order_events = reader.replay_aggregate(
    aggregate_type="order",
    aggregate_id=aggregate_id,
).events

portfolio_events = reader.replay_aggregate(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
).events

state = engine.build(order_events + portfolio_events)

assert state.events_processed >= 4, state
assert aggregate_id in state.orders.orders, state.orders.orders
assert state.orders.orders[aggregate_id]["status"] == "SENT", state.orders.orders[aggregate_id]

pos = state.positions.positions["NGH6@RTSX"]
assert abs(pos["qty"] - 0.0) < 0.000001, pos
assert abs(pos["realized_pnl"] - 10.0) < 0.000001, pos
assert abs(state.portfolio.realized_pnl - 10.0) < 0.000001, state.portfolio
assert abs(state.portfolio.cash_delta - 10.0) < 0.000001, state.portfolio

print("PROJECTION_ENGINE_OK", aggregate_id)
PY
