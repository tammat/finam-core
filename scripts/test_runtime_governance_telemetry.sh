#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/runtime_governance_telemetry.py

python - <<'PY'
from datetime import date

from finam_core.runtime.runtime_governance_telemetry import RuntimeGovernanceTelemetry


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.idx = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        self.idx += 1
        if self.idx == 1:
            return (1, 0, 1, 0)
        if self.idx == 2:
            return (1,)
        return None


class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


class FakePg:
    def __init__(self):
        self.conn = FakeConn()

    def _connect(self):
        return self.conn


pg = FakePg()
telemetry = RuntimeGovernanceTelemetry(pg)

telemetry.write_cycle(
    trade_date=date(2026, 5, 18),
    scorecards_saved=2,
    rank_decisions_saved=2,
    cooldowns_saved=1,
    allocation_count=1,
)

assert pg.conn.commits == 1
assert len(pg.conn.cursor_obj.calls) == 3

insert_sql, params = pg.conn.cursor_obj.calls[-1]

assert "runtime_governance_history" in insert_sql
assert params[1] == 2
assert params[2] == 2
assert params[3] == 1
assert params[4] == 1
assert params[5] == 1
assert params[7] == 1
assert params[9] == 1

print("OK: runtime governance telemetry")
PY
