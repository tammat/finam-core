#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.storage.postgres_logger import PostgresLogger

calls = []

class FakeCursor:
    def execute(self, sql, params):
        calls.append((sql, params))
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

logger = PostgresLogger()
logger.enabled = True
logger._connect = lambda: FakeConn()

logger.log_execution_event(
    event_type="REAL_EXECUTION_RESULT",
    symbol="SBER@MISX",
    side="BUY",
    qty=1,
    price=300,
    status="ACCEPTED",
    reason=None,
    order_id="ord1",
    raw_json={"mode": "real_dry_run"},
)

assert len(calls) == 1, calls
sql, params = calls[0]
assert "INSERT INTO execution_events" in sql
assert params[0] == "REAL_EXECUTION_RESULT"
assert params[1] == "SBER@MISX"
assert params[5] == "ACCEPTED"
assert params[7] == "ord1"

print("OK: PostgresLogger.log_execution_event mock")
PY
