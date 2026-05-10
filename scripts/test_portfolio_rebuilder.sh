#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.events.event_store_reader import EventStoreReader
from finam_core.recovery.portfolio_rebuilder import PortfolioRebuilder

store = EventStore()
reader = EventStoreReader()
rebuilder = PortfolioRebuilder(reader=reader)

aggregate_id = f"portfolio_rebuild_{time.time_ns()}"

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
        "side": "BUY",
        "qty": 1.0,
        "price": 110.0,
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
        "price": 120.0,
    },
)

result = rebuilder.rebuild_aggregate(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
)

pos = result.positions["NGH6@RTSX"]

assert result.events_processed == 3, result
assert pos.qty == 1.0, pos
assert abs(pos.avg_price - 105.0) < 0.000001, pos
assert abs(pos.realized_pnl - 15.0) < 0.000001, pos
assert abs(result.cash_delta - (-90.0)) < 0.000001, result

print("PORTFOLIO_REBUILDER_OK", aggregate_id)
PY
