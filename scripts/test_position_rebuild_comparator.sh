#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time
from dataclasses import dataclass

from finam_core.events.event_store import EventStore
from finam_core.events.event_store_reader import EventStoreReader
from finam_core.recovery.portfolio_rebuilder import PortfolioRebuilder
from finam_core.recovery.position_rebuild_comparator import PositionRebuildComparator
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch


@dataclass
class ManagedPosition:
    symbol: str
    qty: float


class FakePositionsClient:
    def __init__(self, positions):
        self._positions = positions

    def get_positions(self):
        return self._positions


class FakeRepository:
    def __init__(self, positions):
        self._positions = positions

    def list_all(self):
        return self._positions


class FakeManagedService:
    def __init__(self, positions):
        self.repository = FakeRepository(positions)


store = EventStore()
reader = EventStoreReader()
rebuilder = PortfolioRebuilder(reader=reader)
ks = PersistentKillSwitch()
ks.ensure_schema()
ks.deactivate(scope="GLOBAL", reason="test_reset", source="test")

aggregate_id = f"position_compare_{time.time_ns()}"

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

ok_comparator = PositionRebuildComparator(
    portfolio_rebuilder=rebuilder,
    positions_client=FakePositionsClient([
        {"symbol": "NGH6@RTSX", "qty": 1.0},
    ]),
    managed_service=FakeManagedService([
        ManagedPosition(symbol="NGH6@RTSX", qty=1.0),
    ]),
    kill_switch=ks,
)

ok = ok_comparator.compare_aggregate(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
)

assert ok.ok is True, ok
assert ok.reason == "portfolio_rebuild_ok", ok
assert ks.is_active() is False

bad_comparator = PositionRebuildComparator(
    portfolio_rebuilder=rebuilder,
    positions_client=FakePositionsClient([
        {"symbol": "NGH6@RTSX", "qty": 2.0},
    ]),
    managed_service=FakeManagedService([
        ManagedPosition(symbol="NGH6@RTSX", qty=1.0),
    ]),
    kill_switch=ks,
)

bad = bad_comparator.compare_aggregate(
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
)

assert bad.ok is False, bad
assert bad.reason == "portfolio_rebuild_mismatch", bad
assert bad.mismatches[0].kind == "broker_local_qty_mismatch", bad
assert ks.is_active() is True

ks.deactivate(scope="GLOBAL", reason="test_clear", source="test")

print("POSITION_REBUILD_COMPARATOR_OK", aggregate_id)
PY
