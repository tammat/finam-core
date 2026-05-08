#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.storage.real_position_snapshot_repository import RealPositionSnapshotRepository

calls = []

class FakeCursor:
    def executemany(self, sql, rows):
        calls.append((sql, rows))
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class FakeConn:
    def cursor(self):
        return FakeCursor()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

repo = RealPositionSnapshotRepository(database_url="fake")
repo._connect = lambda: FakeConn()

saved = repo.save_positions([
    {"symbol": "BRN6@RTSX", "qty": 2, "avg_price": 64.2, "market_price": 65.1, "unrealized_pnl": 1.8}
])

assert saved == 1
assert "INSERT INTO real_position_snapshots" in calls[0][0]
assert calls[0][1][0][0] == "BRN6@RTSX"

print("REAL_POSITION_SNAPSHOT_REPOSITORY_MOCK_OK")
PY
