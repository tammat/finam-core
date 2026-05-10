#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time
from dataclasses import dataclass

from finam_core.events.event_store import EventStore
from finam_core.oms.order_journal import OmsOrderJournal
from finam_core.reconciliation.startup_recovery_gate import StartupRecoveryGate
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch


@dataclass
class ManagedPosition:
    symbol: str
    qty: float
    stop_order_id: str | None = "broker_order_001"
    tp1_order_id: str | None = "broker_order_001"
    tp2_order_id: str | None = "broker_order_001"
    execution_mode: str = "real"


class FakeRepository:
    def __init__(self, positions):
        self._positions = positions

    def list_all(self):
        return self._positions


class FakeManagedService:
    def __init__(self, positions):
        self.repository = FakeRepository(positions)


class FakeOrdersClient:
    def __init__(self, orders):
        self._orders = orders

    def get_orders(self):
        return self._orders


class FakePositionsClient:
    def __init__(self, positions):
        self._positions = positions

    def get_positions(self):
        return self._positions


ks = PersistentKillSwitch()
ks.ensure_schema()
ks.deactivate(scope="GLOBAL", reason="startup_rebuild_test_reset", source="test")

store = EventStore()
store.ensure_schema()

journal = OmsOrderJournal()
journal.ensure_schema()

aggregate_id = f"startup_rebuild_{time.time_ns()}"

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

client_order_id = journal.build_client_order_id(
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    strategy="startup_rebuild_test",
    ts_bucket=str(time.time_ns()),
)

journal.create_if_absent(
    client_order_id=client_order_id,
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    order_type="LIMIT",
    status="CREATED",
    source="startup_rebuild_test",
    payload={"test": True},
)

orders = [{
    "client_order_id": client_order_id,
    "order_id": "broker_order_001",
    "symbol": "NGH6@RTSX",
    "status": "PENDING_NEW",
}]

gate_ok = StartupRecoveryGate(
    orders_client=FakeOrdersClient(orders),
    managed_service=FakeManagedService([
        ManagedPosition(symbol="NGH6@RTSX", qty=1.0),
    ]),
    positions_client=FakePositionsClient([
        {"symbol": "NGH6@RTSX", "qty": 1.0},
    ]),
    oms_journal=journal,
    rebuild_aggregate_type="portfolio",
    rebuild_aggregate_id=aggregate_id,
)

ok = gate_ok.check()
assert ok.allowed is True, ok
assert ok.reason == "startup_recovery_ok", ok
assert ks.is_active() is False

gate_bad = StartupRecoveryGate(
    orders_client=FakeOrdersClient([]),
    managed_service=FakeManagedService([
        ManagedPosition(symbol="NGH6@RTSX", qty=1.0),
    ]),
    positions_client=FakePositionsClient([
        {"symbol": "NGH6@RTSX", "qty": 2.0},
    ]),
    oms_journal=journal,
    rebuild_aggregate_type="portfolio",
    rebuild_aggregate_id=aggregate_id,
)

bad = gate_bad.check()
assert bad.allowed is False, bad
assert bad.reason == "startup_recovery_freeze", bad
assert any("broker_local_qty_mismatch:NGH6@RTSX" in x for x in bad.issues), bad
assert ks.is_active() is True

ks.deactivate(scope="GLOBAL", reason="startup_rebuild_test_clear", source="test")

print("STARTUP_RECOVERY_GATE_REBUILD_COMPARATOR_OK")
PY
