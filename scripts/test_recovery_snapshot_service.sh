#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.events.event_store import EventStore
from finam_core.events.event_store_reader import EventStoreReader
from finam_core.recovery.portfolio_rebuilder import PortfolioRebuilder
from finam_core.recovery.recovery_snapshot_service import RecoverySnapshotService

aggregate_id = f"snapshot_test_{time.time_ns()}"

store = EventStore()
reader = EventStoreReader()
rebuilder = PortfolioRebuilder(reader=reader)
snapshots = RecoverySnapshotService()

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

rebuild = rebuilder.rebuild_aggregate(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
)

created1, snap1 = snapshots.save_from_rebuild(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
    event_offset=2,
    rebuild_result=rebuild,
    source="test",
)

created2, snap2 = snapshots.save_from_rebuild(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
    event_offset=2,
    rebuild_result=rebuild,
    source="test",
)

assert created1 is True, created1
assert created2 is False, created2
assert snap1.snapshot_id == snap2.snapshot_id

latest = snapshots.latest_snapshot(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
)

assert latest is not None
assert latest.snapshot_id == snap1.snapshot_id
assert latest.event_offset == 2
assert "NGH6@RTSX" in latest.positions
assert abs(float(latest.realized_pnl) - 10.0) < 0.000001, latest

print("RECOVERY_SNAPSHOT_SERVICE_OK", snap1.snapshot_id)
PY
