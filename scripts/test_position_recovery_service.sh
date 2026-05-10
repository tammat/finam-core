#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from dataclasses import dataclass

from finam_core.recovery.position_recovery_service import PositionRecoveryService


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


ok_service = PositionRecoveryService(
    positions_client=FakePositionsClient([
        {"symbol": "NGH6@RTSX", "qty": 1.0},
    ]),
    managed_service=FakeManagedService([
        ManagedPosition(symbol="NGH6@RTSX", qty=1.0),
    ]),
)

ok = ok_service.check()
assert ok.allowed is True, ok
assert ok.reason == "position_recovery_ok", ok

missing_local_service = PositionRecoveryService(
    positions_client=FakePositionsClient([
        {"symbol": "NGH6@RTSX", "qty": 1.0},
    ]),
    managed_service=FakeManagedService([]),
)

missing_local = missing_local_service.check()
assert missing_local.allowed is False, missing_local
assert missing_local.issues[0].kind == "broker_position_missing_locally", missing_local

missing_broker_service = PositionRecoveryService(
    positions_client=FakePositionsClient([]),
    managed_service=FakeManagedService([
        ManagedPosition(symbol="NGH6@RTSX", qty=1.0),
    ]),
)

missing_broker = missing_broker_service.check()
assert missing_broker.allowed is False, missing_broker
assert missing_broker.issues[0].kind == "local_position_missing_at_broker", missing_broker

mismatch_service = PositionRecoveryService(
    positions_client=FakePositionsClient([
        {"symbol": "NGH6@RTSX", "qty": 2.0},
    ]),
    managed_service=FakeManagedService([
        ManagedPosition(symbol="NGH6@RTSX", qty=1.0),
    ]),
)

mismatch = mismatch_service.check()
assert mismatch.allowed is False, mismatch
assert mismatch.issues[0].kind == "broker_local_qty_mismatch", mismatch

print("POSITION_RECOVERY_SERVICE_OK")
PY
