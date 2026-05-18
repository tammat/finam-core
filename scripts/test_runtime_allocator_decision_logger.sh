#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/runtime_allocator_decision_logger.py

python - <<'PY'
from finam_core.runtime.runtime_allocator_decision_logger import RuntimeAllocatorDecisionLogger


class FakeCursor:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))


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
logger = RuntimeAllocatorDecisionLogger(pg)

logger.log_decision(
    symbol="SBER@MISX",
    strategy="VOLATILITY_BREAKOUT_EQUITY",
    regime="trend",
    base_score=0.8,
    strategy_weight=0.25,
    effective_score=0.2,
    selected=True,
    decision_reason="selected_by_effective_score",
    raw_json={"test": True},
)

assert pg.conn.commits == 1
assert len(pg.conn.cursor_obj.calls) == 1

params = pg.conn.cursor_obj.calls[0][1]

assert params[0] == "SBER@MISX"
assert params[1] == "VOLATILITY_BREAKOUT_EQUITY"
assert params[6] is True
assert params[7] == "selected_by_effective_score"

print("OK: runtime allocator decision logger")
PY
