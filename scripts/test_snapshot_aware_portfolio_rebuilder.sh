#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import os
import time

import psycopg2

from finam_core.events.event_store import EventStore
from finam_core.events.event_store_reader import EventStoreReader
from finam_core.recovery.portfolio_rebuilder import PortfolioRebuilder
from finam_core.recovery.recovery_snapshot_service import RecoverySnapshotService
from finam_core.recovery.snapshot_aware_portfolio_rebuilder import SnapshotAwarePortfolioRebuilder

aggregate_id = f"snapshot_aware_{time.time_ns()}"

store = EventStore()
reader = EventStoreReader()
snapshots = RecoverySnapshotService()
portfolio_rebuilder = PortfolioRebuilder(reader=reader)

# base event before snapshot
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

base_rebuild = portfolio_rebuilder.rebuild_aggregate(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
)

with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT max(id)
            FROM event_store
            WHERE aggregate_type = %s
              AND aggregate_id = %s
            """,
            ("portfolio", aggregate_id),
        )
        base_event_offset = int(cur.fetchone()[0])

created, snap = snapshots.save_from_rebuild(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
    event_offset=base_event_offset,
    rebuild_result=base_rebuild,
    source="test",
)

assert created is True, snap

# delta event after snapshot
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

rebuilder = SnapshotAwarePortfolioRebuilder(
    reader=reader,
    snapshots=snapshots,
    rebuilder=portfolio_rebuilder,
)

result = rebuilder.rebuild(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
)

pos = result.positions["NGH6@RTSX"]

assert result.used_snapshot is True, result
assert result.base_event_offset == base_event_offset, result
assert result.delta_events_processed >= 1, result
assert abs(pos.qty - 0.0) < 0.000001, pos
assert abs(pos.realized_pnl - 10.0) < 0.000001, pos
assert abs(result.realized_pnl - 10.0) < 0.000001, result

print("SNAPSHOT_AWARE_PORTFOLIO_REBUILDER_OK", aggregate_id)
PY
