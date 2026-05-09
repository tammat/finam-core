#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time
from dataclasses import dataclass

from finam_core.oms.order_journal import OmsOrderJournal
from finam_core.reconciliation.startup_recovery_gate import StartupRecoveryGate


@dataclass
class ManagedPosition:
    symbol: str
    qty: float
    stop_order_id: str | None = None
    tp1_order_id: str | None = None
    tp2_order_id: str | None = None
    execution_mode: str = "paper"


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


journal = OmsOrderJournal()
journal.ensure_schema()

client_order_id = journal.build_client_order_id(
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    strategy="startup_recovery_test",
    ts_bucket=str(time.time_ns()),
)

created, _ = journal.create_if_absent(
    client_order_id=client_order_id,
    symbol="NGH6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    order_type="LIMIT",
    status="CREATED",
    source="startup_recovery_test",
    payload={"test": True},
)

assert created is True

orders = [{
    "client_order_id": client_order_id,
    "order_id": "broker_startup_001",
    "symbol": "NGH6@RTSX",
    "status": "PENDING_NEW",
}]

managed = FakeManagedService([
    ManagedPosition(
        symbol="NGH6@RTSX",
        qty=1.0,
        stop_order_id="broker_startup_001",
        tp1_order_id="broker_startup_001",
        tp2_order_id="broker_startup_001",
        execution_mode="real",
    ),
])

broker_positions_ok = FakePositionsClient([
    {"symbol": "NGH6@RTSX", "qty": 1.0},
])

gate_ok = StartupRecoveryGate(
    orders_client=FakeOrdersClient(orders),
    managed_service=managed,
    positions_client=broker_positions_ok,
    oms_journal=journal,
)

decision_ok = gate_ok.check()
assert decision_ok.allowed is True, decision_ok
assert decision_ok.reason == "startup_recovery_ok", decision_ok

broker_positions_bad = FakePositionsClient([
    {"symbol": "NGH6@RTSX", "qty": 2.0},
])

gate_bad = StartupRecoveryGate(
    orders_client=FakeOrdersClient([]),
    managed_service=managed,
    positions_client=broker_positions_bad,
    oms_journal=journal,
)

decision_bad = gate_bad.check()
assert decision_bad.allowed is False, decision_bad
assert decision_bad.reason == "startup_recovery_freeze", decision_bad
assert any("broker_local_qty_mismatch:NGH6@RTSX" in x for x in decision_bad.issues), decision_bad

print("STARTUP_RECOVERY_GATE_OK")
PY
